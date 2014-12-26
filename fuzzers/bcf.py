#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Nightmare Fuzzing Project blind coverage fuzzer
@author: joxean
@description: Blind Coverage Fuzzer for Unix/Linux based on DynamoRIO
drcov tool. It's based on a greedy algorithm so don't expect it to 
generate "stellar" results.
"""

import os
import sys
import shutil
import random
import ConfigParser
import simplejson as json

from hashlib import sha1
from subprocess import check_output
from tempfile import mkdtemp, mktemp
from multiprocessing import Process, Manager, Lock, cpu_count

script_path = os.path.dirname(os.path.realpath(__file__))
tmp_path = os.path.join(script_path, "..")
sys.path.append(tmp_path)
tmp_path = os.path.join(tmp_path, "runtime")
sys.path.append(tmp_path)

from nfp_log import log, debug
from nfp_coverage import BININST_AVAILABLE_TOOLS
from nfp_process import RETURN_SIGNALS

#-----------------------------------------------------------------------
class CBlindCoverageFuzzer:
  def __init__(self, arch, cfg, section, metrics=10):
    if int(arch) not in [32, 64]:
      raise Exception("Invalid architecture %s" % str(arch))

    self.arch = arch
    self.cfg = cfg
    self.section = section
    self.metrics = 10
    self.bininst_tool=None

    self.mgr = Manager()
    self.stats = self.mgr.dict()

    self.read_configuration()

    cpus = os.getenv("NIGHTMARE_PROCESSES")
    if cpus is not None:
      cpus = int(cpus)
    else:
      cpus = cpu_count()
    self.procs = cpus

    self.discard_data = self.mgr.list()

    if self.procs > self.metrics:
      log("The number of processes is bigger than the number of metrics, adjusting it to %d" % self.procs)
      self.metrics = self.procs

    # Default output directory is current path
    self.output = "."
    self.input_file = None

    # Maximum number of bytes to mutate per each try
    self.max_size = random.randint(1, 8)
    log("Selected a maximum size of %d change(s) to apply" % self.max_size)
    
    # Only for the iterative mutator
    self.stats["iteration"] = 0
    self.stats["iteration_char"] = 0
    
    self.generations = self.mgr.list()
    self.generation_value = 0
    self.max_generations = 10
    
    self.bugs = 0

  def read_configuration(self):
    if not os.path.exists(self.cfg):
      raise Exception("Invalid configuration file given")

    parser = ConfigParser.SafeConfigParser()
    parser.optionxform = str
    parser.read(self.cfg)

    self.read_target_configuration(parser)
    self.read_bininst_configuration(parser)
    self.read_fuzzer_configuration(parser)
  
  def read_fuzzer_configuration(self, parser):
    """ Read this specific fuzzer additional configuration options from 
        the config file instead of adding a gazilion command line
        options. """
    section = "BCF"
    if section not in parser.sections():
      raise Exception("Binary instrumentation toolkit section %s does not exists in the given configuration file" % section)

    try:
      self.templates_path = parser.get("BCF", 'templates-path')
      debug("Templates path configured to %s" % self.templates_path)
    except:
      self.templates_path = None

  def read_bininst_configuration(self, parser):
    try:
      self.bininst_tool = parser.get("BCF", 'bininst-tool')
      debug("Binary instrumentation tool configured to %s" % self.bininst_tool)
    except:
      raise Exception("Binary instrumentation toolkit parameter bininst-tool does not exists in the given configuration file")

    """ Read the "binary instrumentation toolkit" configuration. """
    if self.bininst_tool not in parser.sections():
      raise Exception("Binary instrumentation toolkit section %s does not exists in the given configuration file" % self.bininst_tool)

    try:
      self.bininst_path = parser.get(self.bininst_tool, 'path')
    except:
      raise Exception("No binary instrumentation toolkit path specified in the configuration file")

  def read_target_configuration(self, parser):
    if self.section not in parser.sections():
      raise Exception("Section %s does not exists in the given configuration file" % self.section)

    try:
      self.pre_command = parser.get(self.section, 'pre-command')
    except:
      # Ignore it, it isn't mandatory
      self.pre_command = None

    try:
      self.post_command = parser.get(self.section, 'post-command')
    except:
      # Ignore it, it isn't mandatory
      self.post_command = None

    try:
      self.command = parser.get(self.section, 'command')
    except:
      raise Exception("No command specified in the configuration file for section %s" % self.section)
    
    try:
      self.tube_name = parser.get(self.section, 'tube')
    except:
      raise
      raise Exception("No tube specified in the configuration file for section %s" % self.section)

    try:
      self.crash_tube = parser.get(self.section, 'crash-tube')
    except:
      self.crash_tube = "%s-crash" % self.tube_name
    
    try:
      self.extension = parser.get(self.section, 'extension')
    except:
      raise Exception("No extension specified in the configuration file for section %s" % self.section)

    try:
      self.timeout = parser.get(self.section, 'timeout')
    except:
      # Default timeout is 90 seconds
      self.timeout = 90
    self.timeout = int(self.timeout)

    try:
      environment = parser.get(self.section, 'environment')
      self.env = dict(parser.items(environment))
    except:
      self.env = {}
    
    try:
      self.cleanup = parser.get(self.section, 'cleanup-command')
    except:
      self.cleanup = None
    
    try:
      self.iterative = parser.getboolean(self.section, 'iterative')
      if self.iterative:
        debug("Iterative algorithm in use")
    except:
      self.iterative = False
    
    try:
      self.save_generations = parser.getboolean(self.section, 'save-generations')
    except:
      self.save_generations = False

    try:
      self.radamsa = bool(parser.get(self.section, 'radamsa'))
      if self.radamsa:
        debug("Radamsa algorithm in use")
    except:
      self.radamsa = False

    try:
      self.state_file = parser.get(self.section, 'state-file')
    except:
      #raise Exception("No state file specified for target %s" % self.section)
      self.state_file = None

    try:
      self.current_state = parser.get(self.section, 'current-state-file')
    except:
      self.current_state = "current-state"

    try:
      is_debug = parser.getboolean(self.section, 'debug')
      config.DEBUG = is_debug
    except:
      # Silently ignore the exception
      pass

    try:
      self.generation_bottom_level = parser.getint(self.section, 'generation-bottom-level')
    except:
      self.generation_bottom_level = -100

    try:
      self.hide_output = parser.getboolean(self.section, 'hide-output')
    except:
      self.hide_output = True

    try:
      self.skip_bytes = parser.getint(self.section, 'skip-bytes')
    except:
      self.skip_bytes = 4
    
    try:
      self.non_uniques = parser.getboolean(self.section, 'non-uniques')
    except:
      self.non_uniques = False

  def record_metric(self, input_file, l):
    cov_tool = BININST_AVAILABLE_TOOLS[self.bininst_tool](self.bininst_path, self.arch)
    if input_file.find(" ") and not input_file.startswith('"'):
      input_file = '"%s"' % input_file

    cmd_line = "%s %s" % (self.command, input_file)
    cov_data = cov_tool.coverage(command=cmd_line, timeout=self.timeout, hide_output=self.hide_output)
    l.append(cov_data)

  def record_metrics(self, input_file):    
    mgr = Manager()
    metrics_data = mgr.list()

    procs = []
    for i in range(self.metrics):
      p = Process(target=self.record_metric, args=(input_file, metrics_data))
      p.start()
      procs.append(p)

      if len(procs) >= self.procs:
        for p in procs:
          p.join()
        procs = []
    
    for p in procs:
      p.join()

    l = set()
    for metric in metrics_data:
      if self.non_uniques:
        l.add(metric.bbs)
      else:
        l.add(metric.unique_bbs)

    self.stats["min"] = min(l)
    self.stats["max"] = max(l)
    self.stats["avg"] = reduce(lambda x, y: x + y, l) / float(len(l))

    self.original_stats = dict(self.stats)
    
    self.print_statistics()

  def print_statistics(self):
    line = "Statistics: Min %d, Max %d, Avg %f, Bugs %d"
    line = line % (self.stats["min"], self.stats["max"], self.stats["avg"], self.bugs)
    log(line)

  def reload_statistics(self):
    if self.state_file is not None:
      with open(self.state_file, "rb") as f:
        self.stats = json.loads(f.read())
    line = "Reloaded statistics: Min %d, Max %d, Avg %f"
    line = line % (self.stats["min"], self.stats["max"], self.stats["avg"])
    log(line)

  def iterative_mutator(self, template):
    debug("Acquiring lock")
    self.lock.acquire()
    try:
      buf = bytearray(template)
      buf[(self.skip_bytes + self.stats["iteration"]) % len(buf)] = chr(self.stats["iteration_char"])
      ret = self.stats["iteration"], 1, buf

      self.stats["iteration_char"] += 1
      if self.stats["iteration_char"] > 255:
        self.stats["iteration_char"] = 0
        self.stats["iteration"] += 1
        log("Current iteration %d" % self.stats["iteration"])
    finally:
      debug("Releasing lock")
      self.lock.release()

    return ret

  def mutate(self, template):
    if self.iterative:
      debug("Iterative2?")
      return self.iterative_mutator(template)
    elif self.radamsa:
      debug("Radamsa")
      return self.mutate_radamsa(template)
    else:
      method = random.randint(0, 3)
      if method == 0:
        debug("Mutate internal")
        return self.mutate_internal(template)
      elif method == 1:
        debug("Mutate from templates")
        return self.mutate_from_templates(template)
      elif method == 2:
        debug("Iterative")
        return self.iterative_mutator(template)
      elif method == 3:
        debug("Radamsa")
        return self.mutate_radamsa(template)

  def mutate_radamsa(self, template):
    filename = mktemp()

    try:
      with open(filename, "wb") as f:
        f.write(template)
      ret = check_output(["radamsa", filename])
      ret = 0, len(ret), ret
    finally:
      os.remove(filename)

    return ret

  def mutate_from_templates(self, template):
    while 1:
      filename = random.choice(os.listdir(self.templates_path))
      filename = os.path.join(self.templates_path, filename)
      if os.path.isfile(filename):
        break

    debug("Randomly selected template file %s" % filename)
    buf = open(filename, "rb").read()
    # TODO: Check this...
    size = random.randint(0, self.max_size)
    offset = 0
    if  min(len(buf)-size, len(template)-size)>self.skip_bytes:
      offset = random.randint(self.skip_bytes, min(len(buf)-size, len(template)-size))
    else:
     offset = self.skip_bytes

    chunk = buf[offset:offset+size]

    buf = bytearray(template)

    # Let's flip a coin to choose if we are going to put in the same 
    # offset as the template file or in a random location
    if random.randint(0, 1) == 1 and offset+size < len(chunk):
      offset = random.randint(0, len(chunk)-offset+size)

    buf[offset:offset+size] = chunk
    return offset, size, chunk

  def mutate_internal(self, template):
    while 1:
      buf = bytearray(template)
      key = None
      size = random.randint(0, self.max_size)
      offset = 0
      if len(buf)-size>self.skip_bytes:
        offset = random.randint(self.skip_bytes, len(buf)-size)
      else:
        offset = self.skip_bytes 

      values = []
      for i in range(size):
        c = random.randint(0, 255)
        values.append(chr(c))

      if [offset, size, "".join(values)] in self.discard_data or \
         template[offset:offset+size] == "".join(values):
        debug("Generated a mutated block with already discarded data...")
        continue
      break

    for i in range(size):
      buf[offset+i%len(buf)] = values[i%len(values)]

    return offset, size, buf

  def dump_poc(self, fuzz_file, offset, size, buf):
    file_hash = sha1(buf).hexdigest()
    log("Output path configured to %s" % self.output)
    filename = os.path.join(self.output, file_hash)
    
    f = open(filename, "wb")
    f.write(buf)
    f.close()
    log("Created proof of concept %s" % filename)

    filename = "%s.diff" % filename
    f = open(filename, "wb")
    f.write("# Original file created by 'Blind Coverage Fuzzer' was %s\n" % self.input_file)
    f.write("%d,%d" % (offset, size))
    f.close()
    log("Created diff file %s" % filename)

  def apply_bytes(self, offset, size, buf):
    debug("Acquiring lock...")
    self.lock.acquire()
    try:
      debug("Saving old generation (%s)" % sha1(self.template).hexdigest())
      if len(self.generations) >= self.max_generations:
        del self.generations[0]
      self.generations.append([bytearray(self.template), dict(self.stats), self.generation_value])
      
      if self.save_generations:
        file_hash = sha1(buf).hexdigest()
        ext = os.path.splitext(self.input_file)[1]
        filename = "generation_%s%s" % (file_hash, ext)
        filename = os.path.join(self.output, filename)
        log("Writing discovered generation file %s (%s)" % (file_hash, filename))

        with open(filename, "wb") as f:
          f.write(buf)

      if not self.radamsa:
        debug("Applying patch at offset %d of size %d" % (offset, size))
      else:
        debug("Replacing old buffer")

      self.template = buf
      """
      if self.skip_bytes > 0:
        header = self.template[0:self.skip_bytes]

      if len(buf) > len(self.template):
        self.template = bytearray(buf)
      else:
        for i in range(size):
          self.template[offset+i] = buf[i]

      if self.skip_bytes > 0:
        self.template[0:self.skip_bytes] = header
      """

      if self.current_state is not None:
        ext = os.path.splitext(self.input_file)[1]
        filename = "%s%s" % (self.current_state, ext)
        filename = os.path.join(self.output, filename)
        file_hash = sha1(self.template).hexdigest()

        debug("Creating or updating current state file %s (%s)" % (filename, file_hash))
        with open(filename, "wb") as f:
          f.write(self.template)

    finally:
      debug("Releasing lock...")
      self.lock.release()

  def discard_bytes(self, offset, size, buf):
    self.discard_data.append([offset, size, buf[offset:offset+size]])

  def fuzz_one(self, template):
    try:
      self.fuzz_one_internal(template)
    except KeyboardInterrupt:
      print "Aborted."
  
  def recalculate_statistics(self, old_stats, bbs):
    self.stats["max"] = bbs
    self.stats["min"] = old_stats["max"]
    self.stats["avg"] = (self.stats["max"] + self.stats["min"]) / 2.
    #self.stats = self.mgr.dict(self.stats)
    line = "New statistics: Min %d, Max %d, Avg %f"
    line = line % (self.stats["min"], self.stats["max"], self.stats["avg"])
    log(line)

    if self.state_file is not None:
      with open(self.state_file, "wb") as f:
        f.write(json.dumps(dict(self.stats)))

  def fuzz_one_internal(self, template):
    # Get mutated data using @template as the template buffer.
    offset, size, buf = self.mutate(template)

    filename = mktemp(suffix = self.extension)
    debug("Creating temporary file %s" % filename)
    with open(filename, "wb") as f:
      f.write(buf)

    debug("Performing code coverage...")
    metrics = []
    self.record_metric(filename, metrics)

    for metric in metrics:
      bbs = int(metric.unique_bbs)
      if len(metric.all_unique_bbs-self.stats["all"])>0:
        if len(self.stats["all"])==0:
          log("=+= Found yet unseen basic block! Saving to templates.")
          shutil.copyfile(filename,os.path.join(self.templates_path,os.path.basename(filename)))

        self.stats["all"]=self.stats["all"] | metric.all_unique_bbs

      if bbs > self.stats["max"]:
        if not self.radamsa:
          log("GOOD! Found an interesting change at 0x%x! Covered basic blocks %d, original maximum %d" % (offset, bbs, self.stats["max"]))
        else:
          log("GOOD! Found an interesting change! Covered basic blocks %d, original maximum %d" % (bbs, self.stats["max"]))
        if self.iterative:
          self.stats["iteration_char"] = 0
          self.stats["iteration"] += 1
        
        increase = (bbs - self.stats["max"])
        self.generation_value += increase
        self.apply_bytes(offset, size, buf)
        self.generation_value = 0

        old_stats = self.mgr.dict(self.stats)
        self.lock.acquire()
        try:
          debug("Recalculating statistics...")
          self.recalculate_statistics(old_stats, bbs)
        finally:
          self.lock.release()
      elif bbs < self.stats["min"]:
        debug("Bad metric found: minimum basic block(s) %d, current test-case basic block(s) %d" % (self.stats["min"], bbs))
        self.discard_bytes(offset, size, buf)
        self.generation_value -= 3
      else:
        line = "Uninteresting data with current test-case: min %d, max %d, current %d"
        line = line % (self.stats["min"], self.stats["max"], bbs)
        debug(line)
        self.discard_bytes(offset, size, buf)
        self.generation_value -= 1

      if metric.exit_code in RETURN_SIGNALS:
        self.generation_value += abs(self.generation_bottom_level)
        ret = metric.exit_code
        log("*** Found a BUG, caught signal %d (%s), hurra!" % (ret, RETURN_SIGNALS[ret]))
        self.dump_poc(filename, offset, size, buf)
        self.bugs += 1

    debug("Removing test-case %s" % filename)
    os.remove(filename)
  
  def show_generation(self, i):
    line = "Iteration %d, current generation value %d, total generation(s) preserved %d"
    line = line % (i, self.generation_value, len(self.generations))
    log(line)

  def fuzz(self, input_file, output, max_iterations=0):
    log("Input file is %s" % input_file)
    self.input_file = input_file
    self.output = output

    loaded = False
    if self.state_file is not None and os.path.exists(self.state_file):
      try:
        log("Loading saved state...")
        self.reload_statistics()
        loaded = True
      except:
        log("Error loading saved state: %s" % sys.exc_info()[1])
    
    if not loaded:  
      log("Recording a total of %d value(s) of coverage..." % self.metrics)
      self.record_metrics(input_file)

    self.template = bytearray(open(input_file, "rb").read())
    self.lock = Lock()

    if max_iterations != 0:
      log("Maximizing file in %d iteration(s)" % max_iterations)
    else:
      log("Fuzzing...")

    i = 0
    while 1:
      # Re-read the configuration on each try
      self.read_configuration()

      if max_iterations != 0 and i > max_iterations:
        break

      if self.generation_value < self.generation_bottom_level and len(self.generations) > 0:
        log("Dropping current generation and statistics as we have too many bad results")
        self.template, self.stats, self.generation_value = self.generations.pop()
        self.print_statistics()
        self.show_generation(i)
      self.fuzz_one(self.template)
      i += 1

      if (i % 10 == 0 and max_iterations != 0) or i % 100 == 0:
        self.show_generation(i)

    # Return the maximized file
    return self.template

#-----------------------------------------------------------------------
def usage():
  print "Usage:", sys.argv[0], "(32|64) <config file> <section> <input_file> <output directory>"
  print
  print "The first argument to", sys.argv[0], "is the architecture, 32bit or 64bit."

#-----------------------------------------------------------------------
def main(arch, cfg, section, input_file, output, max_iterations=0):
  try:
    fuzzer = CBlindCoverageFuzzer(arch, cfg, section)
    buf = fuzzer.fuzz(input_file, output, max_iterations)

    min1 = fuzzer.stats["min"]
    max1 = fuzzer.stats["max"]
    min2 = fuzzer.original_stats["min"]
    max2 = fuzzer.original_stats["max"]

    if max2 < max1:
      log("File successfully maximized from min %d, max %d to min %d, max %d" % (min2, max2, min1, max1))
      filename = "%s.max" % sha1(buf).hexdigest()
      filename = os.path.join(output, filename)
      with open(filename, "wb") as f:
        f.write(buf)
      log("File %s writen to disk" % filename)
    else:
      log("Failed to maximize input file :(")
  except KeyboardInterrupt:
    print "Aborted."

if __name__ == "__main__":
  if len(sys.argv) == 6:
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
  elif len(sys.argv) == 7:
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], int(sys.argv[6]))
  else:
    usage()
