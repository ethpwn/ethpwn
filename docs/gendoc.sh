cd ../

echo "Generating docs for modules with pydoc-markdown..."
set -x
pwd
DIRS_TO_IGNORE="__pycache__|exploit_templates|__init__.py"
for dir in ./src/ethpwn/ethlib/*; do
    if [[ $dir =~ $DIRS_TO_IGNORE ]]; then
        continue
    fi

    # subdirectory
    if [ -d "$dir" ]; then
        pydoc-markdown -I src -m ethpwn.ethlib.${dir##*/} --render-toc > ./docs/docs/ethpwn/modules/${dir##*/}.md
    fi
    # python file
    if [ -f "$dir" ] && [ "${dir##*.}" == "py" ]; then
        module_name=$(basename $dir .py)
        module_path="ethpwn.ethlib.${module_name}"
        pydoc-markdown -I src -m ${module_path} > ./docs/docs/ethpwn/modules/${module_name}.md
    fi
done