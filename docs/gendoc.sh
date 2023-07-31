cd ../

echo "Generating docs for modules with pydoc-markdown..."
pydoc-markdown -I src -m ethpwn.ethlib.currency_utils --render-toc > ./docs/docs/ethpwn/modules/currency_utils.md
pydoc-markdown -I src -m ethpwn.ethlib.global_context --render-toc > ./docs/docs/ethpwn/modules/global_context.md
pydoc-markdown -I src -m ethpwn.ethlib.hashes --render-toc > ./docs/docs/ethpwn/modules/hashes.md
pydoc-markdown -I src -m ethpwn.ethlib.serialization_utils --render-toc > ./docs/docs/ethpwn/modules/serialization_utils.md
pydoc-markdown -I src -m ethpwn.ethlib.transactions --render-toc > ./docs/docs/ethpwn/modules/transactions.md
pydoc-markdown -I src -m ethpwn.ethlib.utils --render-toc > ./docs/docs/ethpwn/modules/utils.md
pydoc-markdown -I src -m ethpwn.ethlib.contract_metadata --render-toc > ./docs/docs/ethpwn/modules/contract_metadata.md
pydoc-markdown -I src -m ethpwn.ethlib.contract_registry --render-toc > ./docs/docs/ethpwn/modules/contract_registry.md
