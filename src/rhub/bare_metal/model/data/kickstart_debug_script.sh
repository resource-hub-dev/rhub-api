#!/bin/bash

# based on https://access.redhat.com/solutions/20358

cd /tmp; mkdir cmd-outputs
W() { local OutputFile=$(tr ' /' '_' <<<"$@"); $@ >cmd-outputs/$OutputFile; }
if [[ ! -f ks.cfg ]] && [[ ! -f /run/install/ks.cfg ]]; then echo No kickstart present >ks.cfg; fi
ls anaconda-tb-* &>/dev/null || kill -USR2 $(</var/run/anaconda.pid)
W cat /mnt/sysimage/root/anaconda-ks.cfg
W cat /run/install/ks.cfg
W cat /tmp/anaconda-tb-*
W cat /tmp/anaconda.log
W cat /tmp/dbus.log
W cat /tmp/dnf.librepo.log
W cat /tmp/hawkey.log
W cat /tmp/ifcfg.log
W cat /tmp/packaging.log
W cat /tmp/program.log
W cat /tmp/storage.log
W cat /tmp/syslog
W cat /tmp/yum.log
W date
W dmesg
W dmidecode
W lspci -vvnn
W fdisk -cul
W parted -l
W ls -lR /dev
W dmsetup ls --tree
W lvm pvs
W lvm vgs
W lvm lvs
W cat /proc/partitions
W mount
W df -h
W cat /proc/meminfo
W cat /proc/cpuinfo
W ps axf
W lsof
W ip -s li
W ip a
W ip r
date=$(date +%F)
tar cvjf install-logs-$date.tbz *log cmd-outputs anaconda-tb-* ks.cfg
echo -e "\nFinished gathering data\nUploading /tmp/install-logs-$date.tbz to Resource Hub\n"
