#!/usr/bin/env perl

# This script is part of TuxMake.
#
# This script for extracts metadata from the build runtime environment in a
# single shot. It should receive a file containing a metadata extraction
# specification in JSON format as its first argument. The format is the
# following:
#
# {
#   "section1": {
#     "key1": "command1 ...",
#     "key2": "command2 ...",
#     [...]
#     "keyN": "commandN ..."
#   },
#   "section2": {
#     "key1": "command1 ...",
#     "key2": "command2 ...",
#     [...]
#     "keyN": "commandN ..."
#   },
#   [...]
# }
#
# The script will read this JSON, then replace each command by its output, and
# print the resulting JSON to stdout. Any output to stderr produced by the
# commands is not touched and still ends up in stderr.

use strict;
use warnings;
use JSON::PP;
use File::Temp;

my $json = JSON::PP->new->utf8->pretty->indent(4);
my @input = <>;
my $metadata = $json->decode(join("", @input));

my $tempdir = File::Temp->newdir();
for my $section (keys(%$metadata)) {
  for my $key (keys(%{$metadata->{$section}})) {
    my $cmd = $metadata->{$section}->{$key};
    my $file = File::Temp->new(DIR => $tempdir);
    print $file $cmd;
    close $file;
    my $script = $file->filename;

    my $result = `sh ${script} 2>/dev/null`;
    chomp $result if $result;
    $metadata->{$section}->{$key} = $result;
  }
}
print($json->encode($metadata));
