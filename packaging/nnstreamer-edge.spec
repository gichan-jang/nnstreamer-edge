%define     test_script $(pwd)/packaging/run_unittests.sh

# Default features for Tizen releases
%define     mqtt_support 1
%define     custom_connection_support 1

# Define features for TV releases
%if "%{?profile}" == "tv"
%define     mqtt_support 0
%endif

%bcond_with tizen

Name:       nnstreamer-edge
Summary:    Common library set for nnstreamer-edge
# Synchronize the version of nnstreamer-edge library.
# 1. CMake : ./CMakeLists.txt
# 2. Ubuntu : ./debian/changelog
# 3. Tizen : ./packaging/nnstreamer-edge.spec
# 4. TizenRT : ./tools/build_TizenRT/Makefile
Version:    0.2.6
Release:    1
Group:      Machine Learning/ML Framework
Packager:   Sangjung Woo <sangjung.woo@samsung.com>
License:    Apache-2.0
Source0:    %{name}-%{version}.tar.gz
Source1001: nnstreamer-edge.manifest

BuildRequires:  cmake

%if %{with tizen}
BuildRequires:  pkgconfig(dlog)
%endif

%if 0%{?mqtt_support}
BuildRequires:  pkgconfig(libmosquitto)
%endif

%if 0%{?unit_test}
BuildRequires:  gtest-devel
BuildRequires:  procps
BuildRequires:  mosquitto

%if 0%{?testcoverage}
BuildRequires:  lcov
%endif
%endif

%description
nnstreamer-edge provides remote source nodes for NNStreamer pipelines without GStreamer dependencies.
It also contains communication library for sharing server node information & status.

%package devel
Summary: development package for nnstreamer-edge
Requires: nnstreamer-edge = %{version}-%{release}
%description devel
It is a development package for nnstreamer-edge.

%if 0%{?unit_test}
%package unittest
Summary: test program for nnstreamer-edge library
%description unittest
It is a test program for nnstreamer-edge library.

%if 0%{?testcoverage}
%package unittest-coverage
Summary: Unittest coverage result for nnstreamer-edge
%description unittest-coverage
HTML pages of lcov results of nnstreamer-edge generated during rpm build
%endif
%endif

%if %{with tizen}
%define enable_tizen -DENABLE_TIZEN=ON
%else
%define enable_tizen -DENABLE_TIZEN=OFF
%endif

%if 0%{?unit_test}
%define enable_unittest -DENABLE_TEST=ON
%else
%define enable_unittest -DENABLE_TEST=OFF
%endif

%if 0%{?mqtt_support}
%define enable_mqtt -DMQTT_SUPPORT=ON
%else
%define enable_mqtt -DMQTT_SUPPORT=OFF
%endif

%if 0%{?custom_connection_support}
%define enable_custom_connection -DENABLE_CUSTOM_CONNECTION=ON
%else
%define enable_custom_connection -DENABLE_CUSTOM_CONNECTION=OFF
%endif

%prep
%setup -q
cp %{SOURCE1001} .

%build

%if 0%{?unit_test}
%if 0%{?testcoverage}
# To test coverage, disable optimizations (and should unset _FORTIFY_SOURCE to use -O0)
CFLAGS=`echo $CFLAGS | sed -e "s|-O[1-9]|-O0|g"`
CFLAGS=`echo $CFLAGS | sed -e "s|-Wp,-D_FORTIFY_SOURCE=[1-9]||g"`
CXXFLAGS=`echo $CXXFLAGS | sed -e "s|-O[1-9]|-O0|g"`
CXXFLAGS=`echo $CXXFLAGS | sed -e "s|-Wp,-D_FORTIFY_SOURCE=[1-9]||g"`

export CFLAGS+=" -fprofile-arcs -ftest-coverage -g"
export CXXFLAGS+=" -fprofile-arcs -ftest-coverage -g"
export FFLAGS+=" -fprofile-arcs -ftest-coverage -g"
export LDFLAGS+=" -lgcov"
%endif
%endif # unittest

mkdir -p build
pushd build
%cmake .. \
    -DCMAKE_INSTALL_PREFIX=%{_prefix} \
    -DVERSION=%{version} \
    %{enable_tizen} %{enable_unittest} %{enable_mqtt} %{enable_custom_connection}

make %{?jobs:-j%jobs}
popd

%install
rm -rf %{buildroot}
pushd build
%make_install
popd

%if 0%{?testcoverage}
# Capture initial zero coverage data. This will be merged with actual coverage data later.
# This is to prevent null gcda file error if the test is not performed (in case of gcov package generation mode).
pushd build
rm -r CMakeFiles
lcov -i -c -o unittest_base.info -d . -b $(pwd) --ignore-errors mismatch
popd
%endif # testcoverage

%if 0%{?unit_test}
LD_LIBRARY_PATH=./src bash %{test_script} ./tests/unittest_nnstreamer-edge

%if 0%{?custom_connection_support}
LD_LIBRARY_PATH=./src:./tests bash %{test_script} ./tests/unittest_nnstreamer-edge-custom
%endif

%if 0%{?mqtt_support}
LD_LIBRARY_PATH=./src bash %{test_script} ./tests/unittest_nnstreamer-edge-mqtt
%endif

%if 0%{?testcoverage}
# 'lcov' generates the date format with UTC time zone by default. Let's replace UTC with KST.
# If you can get a root privilege, run ln -sf /usr/share/zoneinfo/Asia/Seoul /etc/localtime
TZ='Asia/Seoul'; export TZ

# Get commit info
VCS=`cat ${RPM_SOURCE_DIR}/nnstreamer-edge.spec | grep "^VCS:" | sed "s|VCS:\\W*\\(.*\\)|\\1|"`

# Create human readable coverage report web page.
# Generate report and exclude test files.
# Set different lcov options for Tizen/lcov versions.
%if 0%{tizen_version_major} >= 9
lcov -t 'NNStreamer-edge unittest coverage' -o unittest_test.info -c -d . -b %{builddir} --no-external --ignore-errors mismatch,empty
lcov -a unittest_base.info -a unittest_test.info -o unittest_total.info --ignore-errors mismatch,empty
lcov -r unittest_total.info "*/tests/*" -o unittest-filtered.info --ignore-errors graph,unused
%else
lcov -t 'NNStreamer-edge unittest coverage' -o unittest.info -c -d . -b $(pwd) --no-external
lcov -r unittest.info "*/tests/*" -o unittest-filtered.info
%endif # tizen_version_major >= 9
# Visualize the report
genhtml -o result unittest-filtered.info -t "NNStreamer-edge %{version}-%{release} ${VCS}" --ignore-errors source -p ${RPM_BUILD_DIR}

mkdir -p %{buildroot}%{_datadir}/nnstreamer-edge/unittest/
cp -r result %{buildroot}%{_datadir}/nnstreamer-edge/unittest/
%endif # testcoverage
%endif # unittest

%clean
rm -rf %{buildroot}

%files
%manifest nnstreamer-edge.manifest
%defattr(-,root,root,-)
%license LICENSE
%{_libdir}/libnnstreamer-edge.so*

%files devel
%{_includedir}/nnstreamer/nnstreamer-edge.h
%{_includedir}/nnstreamer/nnstreamer-edge-data.h
%{_includedir}/nnstreamer/nnstreamer-edge-event.h
%{_libdir}/pkgconfig/nnstreamer-edge.pc
%if 0%{?custom_connection_support}
%{_includedir}/nnstreamer/nnstreamer-edge-custom.h
%endif

%if 0%{?unit_test}
%files unittest
%manifest nnstreamer-edge.manifest
%defattr(-,root,root,-)
%{_bindir}/unittest_nnstreamer-edge
%if 0%{?custom_connection_support}
%{_bindir}/unittest_nnstreamer-edge-custom
%{_libdir}/libnnstreamer-edge-custom-test.so*
%endif
%if 0%{?mqtt_support}
%{_bindir}/unittest_nnstreamer-edge-mqtt
%endif

%if 0%{?testcoverage}
%files unittest-coverage
%{_datadir}/nnstreamer-edge/unittest/*
%endif
%endif # unittest

%changelog
* Mon Sep 02 2024 Sangjung Woo <sangjung.woo@samsung.com>
- Release of 0.2.6 (Tizen 9.0 M2)

* Fri Sep 15 2023 Sangjung Woo <sangjung.woo@samsung.com>
- Start development of 0.2.5 for next release (0.2.6)

* Tue Sep 12 2023 Sangjung Woo <sangjung.woo@samsung.com>
- Release of 0.2.4 (Tizen 8.0 M2)

* Tue Jun 13 2023 Sangjung Woo <sangjung.woo@samsung.com>
- Start development of 0.2.3 for Tizen 8.0 release (0.2.4)

* Fri Jun 02 2023 Sangjung Woo <sangjung.woo@samsung.com>
- Release of 0.2.2 (LTS for TizenRT)

* Fri Sep 30 2022 Sangjung Woo <sangjung.woo@samsung.com>
- Start development of 0.2.1 for Tizen 7.5 release (0.2.2)

* Fri Jul 1 2022 Sangjung Woo <sangjung.woo@samsung.com>
- Start development of 0.1.0

* Wed Sep 01 2021 Sangjung Woo <sangjung.woo@samsung.com>
- Start development of 0.0.1
