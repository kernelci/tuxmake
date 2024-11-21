Name:      tuxmake
Version:   1.28.5
Release:   0%{?dist}
Summary:   Thin wrapper to build Linux kernels
License:   Expat
URL:       https://tuxmake.org
Source0:   %{pypi_source}


BuildRequires: gcc
BuildRequires: git
BuildRequires: make
BuildRequires: perl-JSON-PP
BuildRequires: python3-devel
BuildRequires: python3-flit
BuildRequires: python3-pip
BuildRequires: python3-pytest
BuildRequires: python3-pytest-cov
BuildRequires: python3-pytest-mock
BuildRequires: wget

BuildArch: noarch

Requires: python3 >= 3.6
Requires: perl-JSON-PP
Recommends: socat

%global debug_package %{nil}

%description
TuxMake is a command line tool and Python library that provides portable and
repeatable Linux kernel builds across a variety of architectures, toolchains,
kernel configurations, and make targets.

%prep
%setup -q

%build
export FLIT_NO_NETWORK=1
make man
make bash_completion

%check
python3 -m pytest test/

%install
mkdir -p %{buildroot}/usr/share/tuxmake/
cp -r run tuxmake %{buildroot}/usr/share/tuxmake/
mkdir -p %{buildroot}/usr/bin
ln -sf ../share/tuxmake/run %{buildroot}/usr/bin/tuxmake
mkdir -p %{buildroot}%{_mandir}/man1
install -m 644 tuxmake.1 %{buildroot}%{_mandir}/man1/
mkdir -p %{buildroot}/usr/share/bash-completion/completions/
install -m 644 bash_completion/tuxmake %{buildroot}/usr/share/bash-completion/completions/

%files
/usr/share/tuxmake
%{_bindir}/tuxmake
%{_mandir}/man1/tuxmake.1*
/usr/share/bash-completion/completions/tuxmake

%doc README.md
%license LICENSE

%changelog

* Wed Dec 23 2020 Antonio Terceiro <antonio.terceiro@linaro.org> - 0.12.0-1
- Initial version of the package

