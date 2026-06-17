target = AnonAddyTB.xpi
static_files = background.js api.js composePopup.js composePopup.html icon.svg manifest.json LICENSE.txt

$(target): dist/
	cd dist && zip -r ../$(target) .

dist/: src/ options.html $(static_files)
	npm run build
	cp $(static_files) dist/

clean:
	-rm -f $(target)
	-rm -rf dist/
