from pathlib import Path

import mkdocs_gen_files

nav = mkdocs_gen_files.Nav()

for path in sorted(Path("sbx_agents").rglob("*.py")):
    if path.name.startswith("_") and path.name != "__init__.py":
        continue

    module_path = path.with_suffix("")
    parts = tuple(module_path.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
        doc_path = Path("reference", *parts, "index.md")
    else:
        doc_path = Path("reference", *parts).with_suffix(".md")

    ident = ".".join(parts)
    nav[parts] = doc_path.relative_to("reference").as_posix()

    with mkdocs_gen_files.open(doc_path, "w") as fd:
        fd.write(f"::: {ident}\n")

    mkdocs_gen_files.set_edit_path(doc_path, path)

with mkdocs_gen_files.open("reference/SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())
