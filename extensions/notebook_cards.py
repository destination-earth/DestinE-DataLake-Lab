from glob import glob
from pathlib import Path
import yaml
import textwrap

def clean_f_string(string):
    return '\n'.join([m.lstrip() for m in string.split('\n')])

def main(app,config):
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
  #domains.remove("book")
  keys = set(keys)

  for domain in domains:
    # domain gallery template
    gallery = textwrap.dedent(
      """
      # {domain} Gallery

      ::::{{grid}} 2
      :gutter: 2
      {grid_cards}
      ::::
    """)

    flist_domain = glob(f"./{domain}/**/*.ipynb", recursive=True)
    grid_cards = []
    for nb in flist_domain:
      new_card = f"""
          :::{{grid-item-card}} title
          :shadow: md
          :link: https://example.com
          :img-top: 
          description
          +++
          footer
          :::
      """
      grid_cards.append(clean_f_string(new_card))
    grid_cards = "\n".join(grid_cards)

    Path(f"./{domain}/gallery.md").write_text(
      gallery.format(
        domain=domain,
        grid_cards=grid_cards
      ))
  
  pass

def setup(app):
    #app.connect("builder-inited", main)
    app.connect("config-inited", main)
    return {
      'version': '0.1',
      'env_version': 1,
      'parallel_read_safe': True,
      'parallel_write_safe': True,
    }