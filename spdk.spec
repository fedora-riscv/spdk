# Global macros

%define deps 1
%define dpdk 0
%define dpdk_build_path "dpdk/build"
%define dpdk_path "dpdk"
%define requirements 0
%define build_requirements 0
%define shared 1
%define rbd 0
%define libdir /usr/local/lib
%define vfio_user 0

# Spec metadata
Name:           spdk
Version:        22.09
Release:        2%{?dist}
Summary:        Storage Performance Development Kit

# This is a minimal set of requirements needed for SPDK apps to run when built with
# default configuration. These are also predetermined by rpmbuild. Extra requirements
# can be defined through a comma-separated list passed via $requirements when building
# the spec.
Requires: glibc
Requires: libaio
Requires: libgcc
Requires: libstdc++
Requires: libuuid
Requires: ncurses-libs
Requires: numactl-libs
Requires: openssl-libs
Requires: zlib
Requires: dpdk
BuildRequires: gcc
BuildRequires: g++
BuildRequires: pkg-config
BuildRequires: dpdk-devel
BuildRequires: make
BuildRequires: liburing
BuildRequires: CUnit-devel
BuildRequires: libuuid-devel
BuildRequires: libaio-devel
BuildRequires: openssl-devel
BuildRequires: libiscsi-devel
BuildRequires: ncurses-devel
BuildRequires: json-c-devel
BuildRequires: libcmocka-devel
BuildRequires: clang
BuildRequires: clang-devel
BuildRequires: python3-pip
BuildRequires: meson
BuildRequires: ninja-build

%if %{requirements}
Requires: %(echo "%{requirements_list}")
%endif

BuildRequires: python3-devel

%if %{build_requirements}
BuildRequires: %(echo "%{build_requirements_list}")
%endif

License:       BSD
URL:           https://spdk.io
Source0:       https://github.com/spdk/spdk/archive/refs/tags/v%{version}.tar.gz

%description

The Storage Performance Development Kit (SPDK) provides a set of tools and libraries for
writing high performance, scalable, user-mode storage applications. It achieves high
performance by moving all of the necessary drivers into userspace and operating in a
polled mode instead of relying on interrupts, which avoids kernel context switches and
eliminates interrupt handling overhead.

%prep
make clean %{make} &>/dev/null || :
%setup

%build
set +x

cfs() {
        (($# > 1)) || return 0

        local dst=$1 f

        mkdir -p "$dst"
        shift; for f; do [[ -e $f ]] && cp -a "$f" "$dst"; done
}

cl() {
        [[ -e $2 ]] || return 0

        cfs "$1" $(find "$2" -name '*.so*' -type f -o -type l | grep -v .symbols)
}

# Rely mainly on CONFIG
./configure --disable-unit-tests --disable-tests --with-dpdk
make -j$(nproc)
make DESTDIR=%{buildroot} install

# Include DPDK libs in case --with-shared is in use.
%if %{dpdk}
cfs %{buildroot}/usr/local/lib/dpdk %{dpdk_build_path}/lib/*
# Special case for SPDK_RUN_EXTERNAL_DPDK setup
cl %{buildroot}/usr/local/lib/dpdk %{dpdk_path}/intel-ipsec-mb/
cl %{buildroot}/usr/local/lib/dpdk %{dpdk_path}/isa-l/
%endif

# Include libvfio-user libs in case --with-vfio-user is in use together with --with-shared
%if %{vfio_user} && %{shared}
cl %{buildroot}/usr/local/lib/libvfio-user build/libvfio-user/
%endif
# Try to include extra binaries that were potentially built
cfs %{buildroot}/usr/local/bin build/fio

# And some useful setup scripts SPDK uses
mkdir -p %{buildroot}/usr/libexec/spdk
mkdir -p %{buildroot}/etc/bash_completion.d
mkdir -p %{buildroot}/etc/profile.d
mkdir -p %{buildroot}/etc/ld.so.conf.d
mkdir -p %{buildroot}%{python3_sitelib}

cat <<-EOF > %{buildroot}/etc/ld.so.conf.d/spdk.conf
%{libdir}
/usr/local/lib/dpdk
/usr/local/lib/libvfio-user
EOF

cat <<-'EOF' > %{buildroot}/etc/profile.d/spdk_path.sh
PATH=$PATH:/usr/libexec/spdk/scripts
PATH=$PATH:/usr/libexec/spdk/scripts/vagrant
PATH=$PATH:/usr/libexec/spdk/test/common/config
export PATH
EOF

cfs %{buildroot}/usr/libexec/spdk scripts
cfs  %{buildroot}%{python3_sitelib} python/spdk
ln -s /usr/libexec/spdk/scripts/bash-completion/spdk %{buildroot}/etc/bash_completion.d/

# We need to take into the account the fact that most of the scripts depend on being
# run directly from the repo. To workaround it, create common root space under dir
# like /usr/libexec/spdk and link all potential relative paths the script may try
# to reference.

# setup.sh uses pci_ids.h
ln -s /usr/local/include %{buildroot}/usr/libexec/spdk

%files
/etc/profile.d/*
/etc/bash_completion.d/*
/usr/libexec/spdk/*
/usr/local/bin/*
%{python3_sitelib}/spdk/*


%package devel
Summary: SPDK development libraries and headers

%description devel
SPDK development libraries and headers

%files devel
/usr/local/include/*
%if %{shared}
%{libdir}/lib*.so
%endif

%package libs
Summary:  SPDK libraries

%description libs
SPDK libraries

%files libs
/etc/ld.so.conf.d/*
%{libdir}/lib*.a
%{libdir}/pkgconfig/*.pc
%if %{shared}
%{libdir}/lib*.so.*
%endif

%post libs
ldconfig

%if %{dpdk}
%package dpdk-libs
Summary: DPDK libraries

%description dpdk-libs
DPDK libraries

%files dpdk-libs
/usr/local/lib/dpdk

%post dpdk-libs
ldconfig
%endif

%if %{vfio_user} && %{shared}
%package libvfio-user
Summary: libvfio-user libraries

%description libvfio-user
libvfio-user libraries

%files libvfio-user
/usr/local/lib/libvfio-user

%post libvfio-user
ldconfig
%endif

%changelog
* Fri Apr 28 2023 Milkice Qiu <milkice@milkice.me>
- Optimize spec file

* Thu Jan 19 2023 Milkice Qiu <milkice@milkice.me>
- Port to Fedora Build System

* Tue Feb 16 2021 Michal Berger <michalx.berger@intel.com>
- Initial RPM .spec for the SPDK
