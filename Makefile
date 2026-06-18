target = AnonAddyTB.xpi
static_files = icon.svg manifest.json LICENSE.txt

$(target): dist/
	cd dist && zip -r ../$(target) .

dist/: src/ _locales/ options.html composePopup.html $(static_files)
	npm run build
	cp $(static_files) dist/
	mkdir -p dist/experiment
	cp src/experiment/schema.json dist/experiment/
	cp -r _locales dist/_locales

clean:
	-rm -f $(target)
	-rm -rf dist/

test-marionette:
	cd tests/marionette && uv sync && uv run pytest -v
