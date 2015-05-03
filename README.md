<pre>
#######                                            #####
   #    #    # #    # #    # #####  ###### #####  #     #   ##   ##### ######
   #    #    # #    # ##   # #    # #      #    # #        #  #    #   #
   #    ###### #    # # #  # #    # #####  #    # #  #### #    #   #   #####
   #    #    # #    # #  # # #    # #      #####  #     # ######   #   #
   #    #    # #    # #   ## #    # #      #   #  #     # #    #   #   #
   #    #    #  ####  #    # #####  ###### #    #  #####  #    #   #   ######

                                Version 0.1
                      Copyright (c) 2015 Saul St John
                   http://github.com/sstjohn/thundergate
</pre>

# Introduction #

ThunderGate is a collection of tools for the manipulation of Tigon3 Gigabit
Ethernet controllers, with special emphasis on the Broadcom NetLink 57762,
such as is found in Apple Thunderbolt Gigabit Ethernet adapters.

Tigon3 controllers contain a variety of architectural blocks, including a PCI
endpoint, an 802.3 media access controller, on-chip ram, DMA read and write
engines, nonvolatile storage, and one or more MIPS processors.

These features are exposed by ThunderGate through an easy-to-use Python
interface, allowing for reverse engineering, development, and deployment of
custom firmware and applications. Examples provided include a userspace VFIO
tap driver, a firmware application capable of transparently monitoring
network traffic and host memory, and a PCI option rom containing an EFI boot
services driver which inhibits the employ of Intel I/O MMU address
translation (VT-d).

# Warning #

This is experimental software made available to you under the terms of
the GPLv3. You assume all risks in using it. Please refer to the COPYING file
for details.

# Installation #

These instructions assume a Debian 8 host.

1. Install dependencies:

    ~~~
$ sudo apt-get install build-essential curl texinfo flex git ca-certificates  \
            gnu-efi python python-ctypeslib libgmp-dev libmpfr-dev libmpc-dev    \
            python-capstone ipython
    ~~~

2. Clone repository:

    ~~~
$ git clone http://github.com/sstjohn/thundergate.git
    ~~~

3. Retreive, compile and install cross mips-elf binutils:

    ~~~
$ curl -O http://ftp.gnu.org/gnu/binutils/binutils-2.25.tar.bz2
$ tar xfi binutils-2.25.tar.bz2
$ mkdir binutils-build
$ pushd binutils-build
$ ../binutils-2.25/configure --target=mips-elf --with-sysroot --disable-nls
$ make && sudo make install && popd
    ~~~

4. Retreive, patch, compile and install cross mips-elf GCC 5.1:

    ~~~
$ curl -O http://ftp.gnu.org/gnu/gcc/gcc-5.1.0/gcc-5.1.0.tar.bz2
$ tar xfi gcc-5.1.0.tar.bz2
$ pushd gcc-5.1.0
$ patch -p1 < ../thundergate/misc/gcc-5.1.0-mtigon.patch
$ popd
$ mkdir gcc-build
$ pushd gcc-build
$ ../gcc-5.1.0/configure --target=mips-elf --program-prefix=mips-elf-    \
        --disable-nls --enable-languages=c,c++ --without-headers            \
        --without-llsc --with-tune=r6000 --with-arch=mips2 --disable-biarch \
        --disable-multilib --with-float=soft --without-hard-float
$ make all-gcc && make all-target-libgcc
$ sudo make install-gcc && sudo make install-target-libgcc && popd
    ~~~

5. Compile ThunderGate:

    ~~~
$ cd thundergate
$ make
    ~~~

# Setup #

You should begin by taking a backup image of the factory-released firmware as
it was when you bought the device. This image can be used to restore the device
to a working state in the event that you should break it using ThunderGate.
See `man ethtool` for details on conducting a device firmware dump.

In order to launch ThunderGate, you will need to know the BDF
(Bus-Device-Function) of your Tigon3 device. This information can be
obtained from, e.g., ```lspci```:

~~~
$ sudo lspci -d14e4: | grep Ethernet
0a:00.0 Ethernet controller: Broadcom Corporation NetXtreme BCM57762 Gigabit Ethernet PCIe
~~~

As is commonly the case on Apple hardware, the BDF for the Thunderbolt
Gigabit in this example is '0a:00.0'.

In order to use the userspace tap driver, the network interface device
will need to be bound to the ```vfio-pci``` kernel module:
~~~
$ sudo modprobe vfio-pci
$ echo $BDF | sudo tee /sys/bus/pci/devices/$BDF/driver/unbind
$ echo $BDF | sudo tee /sys/bus/pci/drivers/vfio-pci/bind
~~~

All other functionality is available regardless of the kernel driver in use.

# Usage #

<pre>
$ py/main.py -h
usage: main.py [-h] [-v] [-d] [-t] [-s] device

positional arguments:
  device        BDF of tg3 PCI device

optional arguments:
  -h, --help    show this help message and exit
  -v, --vfio    use vfio interface
  -d, --driver  load userspace tap driver
  -t, --tests   run tests
  -s, --shell   ipython cli
</pre>

## EFI PCI OpRom ##

The example EFI PCI Option Rom code lives under the 'dmarf/' directory. It can
be installed to the target device from the ThunderGate CLI as follows:
~~~
dev.nvram.init(wr=1)
dev.nvram.load_efi_drv("dmarf/dmarf.efi")
~~~

## MIPS CPU firmware application ##

The example Tigon3 MIPS core firmware application code lives under the 'fw/'
directory. It can be installed to the target device from the ThunderGate CLI
as follows:
~~~
dev.nvram.init(wr=1)
dev.load_rxcpu_fw("fw/nvimage")
~~~
