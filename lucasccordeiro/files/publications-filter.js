// Filters the ~200 publication entries in place. Injected from JS so that the
// control never appears unless it can actually work.
(function () {
	var section = document.querySelector('#publications .section-title');
	if (!section) return;

	var entries = Array.prototype.slice.call(section.querySelectorAll('p'));
	var years = Array.prototype.slice.call(section.querySelectorAll('.pub-year'));
	if (entries.length === 0) return;

	var wrap = document.createElement('div');
	wrap.className = 'pub-filter';
	wrap.innerHTML =
		'<label class="sr-only" for="pub-search">Filter publications</label>' +
		'<input type="search" id="pub-search" autocomplete="off"' +
		' placeholder="Filter by title, co-author, venue or year…">' +
		'<span class="pub-count"></span>';

	var heading = section.querySelector('h3');
	heading.parentNode.insertBefore(wrap, heading.nextSibling);

	var input = wrap.querySelector('input');
	var count = wrap.querySelector('.pub-count');

	entries.forEach(function (p) {
		p.dataset.haystack = p.textContent.toLowerCase();
	});

	function apply() {
		var q = input.value.trim().toLowerCase();
		var shown = 0;

		entries.forEach(function (p) {
			var hit = q === '' || p.dataset.haystack.indexOf(q) !== -1;
			p.style.display = hit ? '' : 'none';
			if (hit) shown++;
		});

		// a year heading is only meaningful while one of its entries survives
		years.forEach(function (h) {
			var visible = false;
			for (var el = h.nextElementSibling; el && !el.classList.contains('pub-year'); el = el.nextElementSibling) {
				if (el.tagName === 'P' && el.style.display !== 'none') { visible = true; break; }
				if (el.tagName === 'H4') break;
			}
			h.style.display = visible ? '' : 'none';
		});

		count.textContent = q === ''
			? entries.length + ' publications'
			: shown + ' of ' + entries.length + ' publications';
	}

	input.addEventListener('input', apply);
	apply();
})();
