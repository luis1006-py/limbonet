	const ipPattern =
		"(\\b25[0-5]|\\b2[0-4][0-9]|\\b[01]?[0-9][0-9]?)(\\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}";

	const macPattern =
		"^([0-9A-Fa-f]{2}([-:])){5}([0-9A-Fa-f]{2})$";

	document.querySelectorAll("[data-ip]").forEach(input => {
		input.setAttribute("pattern", ipPattern);
	});

	document.querySelectorAll("[data-mac]").forEach(input => {
		input.setAttribute("pattern", macPattern);
	});