%define ccver CC4
Summary:	An FTP daemon originally developed by Washington University
Name:		wu-ftpd
Version:	2.8.0
Release:	2
License:	BSD
Group:		System/Servers
Source0:	http://www.wfms.org/wu-ftpd/wu-ftpd-%version-%ccver.tar.gz
URL:		http://www.wfms.org/wu-ftpd

Source1:	ftpd.log
Source2:	ftp.pamd
Source3:	wu-ftpd-xinetd
# safe glob.c
Source4:	wu-ftpd-2.6.1-safer-glob.c
Source5:	wu-ftpd.service.bz2
Patch0:		wu-ftpd-2.6.0-redhat-ported.patch
Patch1:		wu-ftpd-2.6.0-owners.patch
Patch11:	wu-ftpd-2.8.0-pasv-port-allow-correction.patch
Patch100:	wu-ftpd-2.6.0-nonrootfix.patch
Provides:	ftpserver, BeroFTPD = 1.4.0
Requires(pre):		rpm-helper
Requires(post):     rpm-helper
Requires(postun):   rpm-helper
Requires(preun):    rpm-helper
Requires(post): xinetd
Requires(postun): xinetd
Requires: xinetd
Obsoletes:	BeroFTPD < 1.4.0
BuildRequires:	byacc

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
%setup -q -n %name-%version-%ccver
mkdir rhsconfig
%patch0 -p1 -b .rh~
%patch1 -p1 -b .owners~
%patch11 -p1 -b .portcorr~
%patch100 -p1 -b .nonroot~
cp %{SOURCE4} src/glob.c

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


%changelog
* Sun Aug 03 2008 Thierry Vignaud <tvignaud@mandriva.com> 2.6.2-12mdv2009.0
+ Revision: 262177
- rebuild

* Wed Jul 30 2008 Thierry Vignaud <tvignaud@mandriva.com> 2.6.2-11mdv2009.0
+ Revision: 256462
- rebuild

* Thu Mar 13 2008 Andreas Hasenack <andreas@mandriva.com> 2.6.2-9mdv2008.1
+ Revision: 187618
- rebuild for 2008.1

  + Olivier Blin <oblin@mandriva.com>
    - restore BuildRoot

  + Thierry Vignaud <tvignaud@mandriva.com>
    - kill re-definition of %%buildroot on Pixel's request

* Thu Jul 19 2007 Olivier Thauvin <nanardon@mandriva.org> 2.6.2-8mdv2008.0
+ Revision: 53517
- require xinetd (thanks PB)
- Import wu-ftpd



* Fri Mar 03 2006 Michael Scherer <misc@mandriva.org> 2.6.2-7mdk
- fix pam stuff
- add avahi service file
- disable quota, it doesn't compile
- add a new patch to make it compil
- fix Prereq
- rename logrotate file

* Thu Jun 02 2005 Nicolas Lécureuil <neoclust@mandriva.org> 2.6.2-6mdk
- Rebuild

* Fri Aug 01 2003 Per Øyvind Karlsen <peroyvind@linux-mandrake.com> 2.6.2-5mdk
- enable more features
- bugfix CAN-2003-0466 off-by-one (P7)
- prereq on rpm-helper (only;)

* Fri Aug 01 2003 Per Øyvind Karlsen <peroyvind@linux-mandrake.com> 2.6.2-4mdk
- rebuild
- macroize
- fix build (P200)

* Sat Jul 20 2002 Geoffrey Lee <snailtalk@mandrakesoft.com> 2.6.2-3mdk
- Re-do add/remove user (lost in space).

* Fri Jul 19 2002 Laurent MONTEL <lmontel@mandrakesoft.com> 2.6.2-2mdk
- Rebuild 
- Fix menu entry

* Mon Dec 31 2001 Geoffrey Lee <snailtalk@mandrakesoft.com> 2.6.2-1mdk
- First attempt at a 2.6.2.

* Fri Nov 30 2001 Vincent Danen <vdanen@mandrakesoft.com> 2.6.1-13mdk
- forgot to include a patch that fixes more globbing stuff in ftpcmd.y

* Wed Nov 28 2001 Vincent Danen <vdanen@mandrakesoft.com> 2.6.1-12mdk
- use safer-glob.c from Olaf Kirch <okir@caldera.de> to fix globbing
  vulnerability

* Sun Sep 09 2001 Stefan van der Eijk <stefan@eijk.nu> 2.6.1-11mdk
- BuildRequires: byacc
- Copyright --> License

* Wed Feb 21 2001 Chmouel Boudjnah <chmouel@mandrakesoft.com> 2.6.1-10mdk
- Remove Requires of netkit-base.

* Wed Jan 10 2001 Vincent Danen <vdanen@mandrakesoft.com> 2.6.1-9mdk
- security fix, apply patch to fix tmpfile problem with privatepw helper

* Tue Jan 09 2001 Vincent Danen <vdanen@mandrakesoft.com> 2.6.1-8mdk
- apply recommended patches: fixes pasv-allow and some format strings

* Tue Sep 26 2000 Chmouel Boudjnah <chmouel@mandrakesoft.com> 2.6.1-7mdk
- Pamstackizification.

* Sat Sep 23 2000 Chmouel Boudjnah <chmouel@mandrakesoft.com> 2.6.1-6mdk
- Upgrade xinetd support.
- Relaunch xinetd condrestart if xinetd is installed.

* Wed Aug 30 2000 Guillaume Cottenceau <gc@mandrakesoft.com> 2.6.1-5mdk
- %%config(noreplace)

* Wed Aug 30 2000 Etienne Faure <etiennemandrakesoft.com> 2.6.1-4mdk
- rebuilt with _mandir macro

* Sat Jul 15 2000 Chmouel Boudjnah <chmouel@mandrakesoft.com> 2.6.1-3mdk
- Add xinetd support.

* Fri Jul  7 2000 Chmouel Boudjnah <chmouel@mandrakesoft.com> 2.6.1-2mdk
- Fix internal ls.
- Remerge with redhat patches, and clean-up.

* Mon Jul  3 2000 Guillaume Cottenceau <gc@mandrakesoft.com> 2.6.1-1mdk
- 2.6.1 (mainly security fixes)

* Mon Jun 26 2000 Chmouel Boudjnah <chmouel@mandrakesoft.com> 2.6.0-7mdk
- Security updates.
- Merge with rh patches.

* Sun May 07 2000 Jerome Martin <jerome@mandrakesoft.com> 2.6.0-6mdk
- use new configure compilation style 
- disable quotas by default to fix conflicts with supermount 
  (floppy I/O errors)

* Mon Apr 10 2000 Geoffrey Lee <snailtalk@linux-mandrake.com>
- make a non root fix for Makefile.in

* Thu Mar 30 2000 John Buswell <johnb@mandrakesoft.com> 2.6.0-4mdk
- Fixed groups
- spec-helper

* Tue Jan 04 2000 John Buswell <johnb@mandrakesoft.com>
- Fixed anon access so that it requires anonftp package
- Added requires for netkit

* Wed Oct 27 1999 Chmouel Boudjnah <chmouel@mandrakesoft.com>
- Merge with rh patchs.
- Real pam support.

* Tue Oct 19 1999 Chmouel Boudjnah <chmouel@mandrakesoft.com>

- 2.6.0.

* Sat Sep 18 1999 Bernhard Rosenkraenzer <bero@linux-mandrake.com>
- 2.6.0pre2
- switch to autoconfed build
- enable support for broken clients
- bzip2 man pages
- Obsoletes: BeroFTPD - this is the first common version. ;)

* Fri Apr 16 1999 Cristian Gafton <gafton@redhat.com>
- crafted the "general use" spec file for automatically building rpms
