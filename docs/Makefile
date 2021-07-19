# Minimal makefile for Sphinx documentation

SPHINXOPTS    =
SPHINXBUILD   = sphinx-build
SPHINXPROJ    = Resource Hub
SOURCEDIR     = .
BUILDDIR      = _build

.PHONY: help
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: Makefile
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: clean
clean:
	$(RM) -r api-code _static/swaggerui
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: api-code
api-code:
	sphinx-apidoc --implicit-namespaces \
		-H "Code API reference" \
		-o $@ ../src/rhub

.PHONY: api-web
api-web:
	mkdir -p _static/swaggerui
	wget -O _static/swaggerui/swagger-ui.css \
		https://unpkg.com/swagger-ui-dist@3.51.1/swagger-ui.css
	prance compile ../src/openapi/openapi.yml _static/swaggerui/openapi.json
