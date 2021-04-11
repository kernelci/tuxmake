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
arc          |             | ARC                      | yes¹     | no
arm64        | *aarch64*   | 64-bit ARMv8             | yes      | yes
arm          |             | 32-bit ARM               | yes      | yes
hexagon      |             | Qualcomm Hexagon (DSP6)  | yes²     | no
i386         |             | 32-bit X86               | yes      | yes
mips         |             | 32-bit MIPS              | yes      | yes
openrisc     |             | OpenRISC                 | no       | no
parisc       |             | 64-bit parisc            | yes      | no
powerpc      |             | 64-bit PowerPC (EL)      | yes      | yes
riscv        |             | 64-bit RISC-V            | yes      | no
s390         |             | 64-bit IBM S/390         | yes      | yes
sh           |             | 32-bit sh4               | yes¹     | no
sparc        |             | 64-bit Sparc             | yes      | no
um           |             | User-Mode Linux          | yes      | no
x86_64       | *amd64*     | 64-bit X86               | yes      | yes

¹ `gcc` only  
² `clang`/`llvm` only
