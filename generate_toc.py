from glob import glob
from pathlib import Path
import textwrap

def clean_string(string):
    return '\n'.join([m.lstrip() for m in string.split('\n')])

def run_toc_generation():
  # find all ipynb files in current project
  ipynb_list = glob(f"./**/*.ipynb", recursive=True)
  domains = []
  keys = []
  for nb in ipynb_list:
    path_parents = nb.split("/")
    domains.append(path_parents[1])
    if len(path_parents) > 3:
      keys.append(path_parents[2])
  domains = set(domains)
  domains.remove("book")
  keys = set(keys)

  # create chapter per domain
  toc = []
  for domain in domains:
    flist_domain = glob(f"./{domain}/**/*.ipynb", recursive=True)
    domain_ipynb = ""
    for nb in flist_domain:
      fname = Path(nb).with_suffix('')
      domain_ipynb += f"- file: {fname}\n"
    domain_ipynb = textwrap.indent(domain_ipynb, "      ", lambda line: True)

    chapter = textwrap.dedent("""
    - caption: {domain_name}
      chapters:
        - file: {domain_name}/README
          title: Overview
        - file: {domain_name}/gallery
          title: {domain_name} - Gallery
          sections:
    {files}
    """)

    toc.append(
      chapter.format(
        domain_name=domain,
        files=domain_ipynb)
    )
  
  # join toc items to single string
  toc_items= "".join(toc)
  #print(toc_items)

  # _toc.yml template to be written
  toc_template = textwrap.dedent(
    """
    format: jb-book
    root: {root_doc}
    parts:
    {toc_entries:>4}
    """
  )
  return toc_template.format(root_doc="README", toc_entries=toc_items)

if __name__ == '__main__':
  #toc_file = f"./book/_toc.yml"
  toc_file = f"./_toc.yml"
  toc = run_toc_generation()
  Path(toc_file).write_text(toc)

  