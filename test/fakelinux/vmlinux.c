/* This is not really the Linux kernel. */

int main(int argc, char** argv) {
  char* timestamp = KBUILD_BUILD_TIMESTAMP;
  char* user = KBUILD_BUILD_USER;
  char* host = KBUILD_BUILD_HOST;
  unsigned int epoch = SOURCE_DATE_EPOCH;
  return 0;
}
