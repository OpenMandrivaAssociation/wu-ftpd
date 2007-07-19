%define version 2.6.2
%define release %mkrel 8

Summary:	An FTP daemon originally developed by Washington University
Name:		wu-ftpd
Version:	%{version}
Release:	%{release}
License:	BSD
Group:		System/Servers
Source:		ftp://ftp.wu-ftpd.org/pub/wu-ftpd/%{name}-%{version}.tar.bz2
URL:		http://www.wu-ftpd.org/

Source1:	ftpd.log
Source2:	ftp.pamd
Source3:	wu-ftpd-xinetd
# safe glob.c
Source4:	wu-ftpd-2.6.1-safer-glob.c
Source5:    wu-ftpd.service.bz2
Patch0:		wu-ftpd-2.6.0-redhat.patch.bz2
Patch1:		wu-ftpd-2.6.0-owners.patch.bz2
Patch2:		wu-ftpd-2.6.1-fixinternalls.patch.bz2
Patch7:		wu-ftpd-2.6.2-realpatch.patch.bz2
Patch11:	wu-ftpd-2.6.1-pasv-port-allow-correction.patch.bz2
Patch12:	wu-ftpd-2.6.1-privatepw.patch.bz2
Patch100:	wu-ftpd-2.6.0-nonrootfix.patch.bz2
Patch200:	wu-ftpd-2.6.2-compilefix.patch.bz2
Patch201:   wu-ftpd-2.6.2-compilefix_sprintf.patch.bz2
Provides:	ftpserver, BeroFTPD
Requires(pre):		rpm-helper
Requires(post):     rpm-helper
Requires(postun):   rpm-helper
Requires(preun):    rpm-helper
Requires(post): xinetd
Requires(postun): xinetd
Requires: xinetd
Obsoletes:	BeroFTPD
BuildRequires:	byacc
Buildroot:	%{_tmppath}/%{name}root

%description
The wu-ftpd package contains the wu-ftpd FTP (File Transfer Protocol)
server daemon.  The FTP protocol is a method of transferring files
between machines on a network and/or over the Internet.  Wu-ftpd's
features include logging of transfers, logging of commands, on the fly
compression and archiving, classification of users' type and location,
per class limits, per directory upload permissions, restricted guest
accounts, system wide and per directory messages, directory alias,
cdpath, filename filter and virtual host support.

Install the wu-ftpd package if you need to provide FTP service to remote
users.

%prep
%setup -q
mkdir rhsconfig
%patch0 -p1 
%patch1 -p1
%patch2 -p1
%patch11 -p0
%patch12 -p1
%patch100 -p1
%patch200 -p1 -b .peroyvind
%patch201 -p0 
cp %{SOURCE4} src/glob.c
%patch7 -p1

%build
%configure --enable-pam --disable-rfc931 --enable-ratios \
	--enable-passwd --enable-ls --disable-dnsretry --enable-ls --enable-ipv6 \
        --enable-tls

perl -pi -e "s,/\* #undef SHADOW_PASSWORD \*/,#define SHADOW_PASSWORD 1,g" src/config.h

make all

%install
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT{%{_sysconfdir},%{_sbindir}}
%makeinstall_std
install -c -m755 util/xferstats $RPM_BUILD_ROOT%{_sbindir}
cd rhsconfig
install -c -m 600 ftpaccess ftpusers  ftphosts ftpgroups ftpconversions $RPM_BUILD_ROOT%{_sysconfdir}
install -D -m 644 %{SOURCE1} $RPM_BUILD_ROOT%{_sysconfdir}/logrotate.d/%{name}
install -D -m 644 %{SOURCE2} $RPM_BUILD_ROOT%{_sysconfdir}/pam.d/ftp
ln -sf in.ftpd $RPM_BUILD_ROOT%{_sbindir}/wu.ftpd
ln -sf in.ftpd $RPM_BUILD_ROOT%{_sbindir}/in.wuftpd

install -D -m644 %{SOURCE3} %buildroot%{_sysconfdir}/xinetd.d/wu-ftpd

mkdir -p %buildroot%{_sysconfdir}/avahi/services/
bzcat %{SOURCE5} > %buildroot%{_sysconfdir}/avahi/services/wu-ftpd.service

%clean
rm -rf $RPM_BUILD_ROOT

%pre
%_pre_useradd ftp /var/ftp /bin/false

%post
if [ ! -f /var/log/xferlog ]; then
    touch /var/log/xferlog
    chmod 600 /var/log/xferlog
fi
/sbin/service xinetd reload > /dev/null 2>&1 || :

%postun
/sbin/service xinetd reload > /dev/null 2>&1 || :
%_postun_userdel ftp

%files
%defattr(-,root,root)
%config(noreplace) %{_sysconfdir}/xinetd.d/wu-ftpd
%doc README ERRATA CHANGES CONTRIBUTORS
%doc doc/HOWTO doc/TODO doc/examples
%{_mandir}/*/*.*
%config(noreplace) %{_sysconfdir}/ftp*
%config(noreplace) %{_sysconfdir}/pam.d/ftp
%config(noreplace) %{_sysconfdir}/logrotate.d/%{name}
%config(noreplace) %{_sysconfdir}/avahi/services/wu-ftpd.service

%defattr(0755,bin,bin)
%{_sbindir}/*
%{_bindir}/*
