# Target architectures

TuxMake supports building for a set of architectures, and they are documented
here in alphabetical order. If you have the corresponding toolchain installed
locally, then you can build that architecture on your host system using the
`null` runtime.

For the container runtimes, the "Kernel" and "Userspace" columns specify
whether the default TuxMake container images for that architecture allow you to
cross build, respectively, the kernel and userspace code (e.g. `perf`).


Architecture | Aliases     | Description              | Kernel   | Userspace
-------------|-------------|--------------------------|----------|----------
alpha        |             | 64-bit RISC              | yes³     | no
arc          |             | ARC                      | yes¹ ³   | no
arm64        | *aarch64*   | 64-bit ARMv8             | yes      | yes
arm          | *armhf*     | 32-bit ARM V7/hardfloat  | yes      | yes
armv5        | *armel*     | 32-bit ARM V5            | yes¹ ²   | yes
csky         |             | 32-bit                   | yes³     | no
hexagon      |             | Qualcomm Hexagon (DSP6)  | yes²     | no
i386         |             | 32-bit X86               | yes      | yes
loongarch    |             | 64-bit LoongArch         | yes³     | no
m68k         |             | 32-bit Motorola          | yes      | yes
microblaze   |             | 32-bit/64-bit RISC       | yes³     | no
mips         |             | 32-bit MIPS              | yes¹ ³   | yes
nios2        |             | 32-bit RISC              | yes³     | no
openrisc     |             | OpenRISC                 | no¹ ³    | no
parisc       |             | 64-bit parisc            | yes¹ ²   | no
powerpc      |             | 64-bit PowerPC           | yes¹ ² ³ | yes
riscv        |             | 64-bit RISC-V            | yes¹ ² ³ | no
s390         | *s390x*     | 64-bit IBM S/390         | yes      | yes
sh           |             | 32-bit sh4               | yes¹     | no
sh2          |             | 32-bit sh2               | yes³     | no
sh4          |             | 32-bit sh4               | yes³     | no
sparc        |             | 64-bit Sparc             | yes¹ ² ³ | no
um           |             | User-Mode Linux          | yes¹ ²   | no
x86_64       | *amd64*     | 64-bit X86               | yes      | yes
xtensa       |             | 32-bit RISC              | yes³     | no

¹ `gcc` only  
² `clang` only
³ `korg-gcc` only
