#!/usr/bin/python2.7

# Copyright 2017 The Bazel Authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http:#www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A script to generate Java class to ObjC header mapping for J2ObjC.

This script generates a text file containing mapping between top-level Java
classes to associated ObjC headers, generated by J2ObjC.

The mapping file is used by dependent J2ObjC transpilation actions to locate
the correct header import paths for dependent Java classes.

Inside the script, we read the Java source files and source jars of a single
Java rule, and parse out the package names from the package statements, using
regular expression matching.

Note that we cannot guarantee 100% correctness by using just regular expression,
but it should be good enough. This allows us to avoid doing any further complex
parsing of the source files and keep the script light-weight without other
dependencies. In the future, we can consider implementing a simple Java lexer
here that correctly parses the package statements out of Java files.
"""

import argparse
import os
import re
import zipfile

_PACKAGE_RE = re.compile(r'(package)\s+([\w\.]+);')


def _get_file_map_entry(java_file_path, java_file):
  """Returns the top-level Java class and header file path tuple.

  Args:
    java_file_path: The file path of the source Java file.
    java_file: The actual file of the source java file.
  Returns:
    A tuple containing top-level Java class and associated header file path. Or
    None if no package statement exists in the source file.
  """
  for line in java_file:
    stripped_line = line.strip()
    package_statement = _PACKAGE_RE.search(stripped_line)

    # We identified a potential package statement.
    if package_statement:
      preceding_characters = stripped_line[0:package_statement.start(1)]
      # We have preceding characters before the package statement. We need to
      # look further into them.
      if preceding_characters:
        # Skip comment line.
        if preceding_characters.startswith('//'):
          continue

        # Preceding characters also must end with a space, represent an end
        # of comment, or end of a statement.
        # Otherwise, we skip the current line.
        if not (preceding_characters[len(preceding_characters) - 1].isspace() or
                preceding_characters.endswith(';') or
                preceding_characters.endswith('*/')):
          continue
      package_name = package_statement.group(2)
      class_name = os.path.splitext(os.path.basename(java_file_path))[0]
      header_file = os.path.splitext(java_file_path)[0] + '.h'
      return (package_name + '.' + class_name, header_file)
  return None


def main():
  parser = argparse.ArgumentParser(fromfile_prefix_chars='@')
  parser.add_argument(
      '--source_files',
      required=False,
      help='The source files')
  parser.add_argument(
      '--source_jars',
      required=False,
      help='The source jars.')
  parser.add_argument(
      '--output_mapping_file',
      required=False,
      help='The output mapping file')

  args, _ = parser.parse_known_args()
  class_to_header_map = {}

  # Process the source files.
  if args.source_files:
    source_files = args.source_files.split(',')
    for source_file in source_files:
      with open(source_file, 'r') as f:
        entry = _get_file_map_entry(source_file, f)
        if entry:
          class_to_header_map[entry[0]] = entry[1]

  # Process the source jars.
  if args.source_jars:
    source_jars = args.source_jars.split(',')
    for source_jar in source_jars:
      with zipfile.ZipFile(source_jar, 'r') as jar:
        for jar_entry in jar.namelist():
          if jar_entry.endswith('.java'):
            with jar.open(jar_entry) as jar_entry_file:
              entry = _get_file_map_entry(jar_entry, jar_entry_file)
              if entry:
                class_to_header_map[entry[0]] = entry[1]

  # Generate the output header mapping file.
  if args.output_mapping_file:
    with open(args.output_mapping_file, 'w') as output_mapping_file:
      for class_name in sorted(class_to_header_map):
        header_path = class_to_header_map[class_name]
        output_mapping_file.write(class_name + '=' + header_path + '\n')

if __name__ == '__main__':
  main()
