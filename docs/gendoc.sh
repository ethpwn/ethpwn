cd ../

echo "Generating docs for modules with pydoc-markdown..."
pydoc-markdown -I src -m ethtools.pwn.currency_utils --render-toc > ./docs/docs/ethpwn/modules/currency_utils.md
pydoc-markdown -I src -m ethtools.pwn.global_context --render-toc > ./docs/docs/ethpwn/modules/global_context.md
pydoc-markdown -I src -m ethtools.pwn.hashes --render-toc > ./docs/docs/ethpwn/modules/hashes.md
pydoc-markdown -I src -m ethtools.pwn.serialization_utils --render-toc > ./docs/docs/ethpwn/modules/serialization_utils.md
pydoc-markdown -I src -m ethtools.pwn.transactions --render-toc > ./docs/docs/ethpwn/modules/transactions.md
pydoc-markdown -I src -m ethtools.pwn.utils --render-toc > ./docs/docs/ethpwn/modules/utils.md
pydoc-markdown -I src -m ethtools.pwn.contract_metadata --render-toc > ./docs/docs/ethpwn/modules/contract_metadata.md
pydoc-markdown -I src -m ethtools.pwn.contract_registry --render-toc > ./docs/docs/ethpwn/modules/contract_registry.md
