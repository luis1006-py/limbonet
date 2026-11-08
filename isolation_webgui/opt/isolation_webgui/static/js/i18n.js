const I18N = {
	lang: "es",
	section: "default",
	data: {},

	async init(section, defaultLang = "es") {
		this.section = section;
		this.lang = localStorage.getItem("lang") || defaultLang;

		await this.load(this.lang, this.section);
		this.translatePage();

		const switcher = document.getElementById("langSwitcher");
		if (switcher) {
			switcher.value = this.lang;
			switcher.addEventListener("change", async (e) => {
				const lang = e.target.value;
				await this.load(lang, this.section);
				this.translatePage();
			});
		}
	},

	async load(lang, section) {
		this.lang = lang;
		this.section = section;

		localStorage.setItem("lang", lang);

		const path = `/static/lang/${lang}/${section}.json`;

		try {
			const res = await fetch(path);
			if (!res.ok) throw new Error("Archivo no encontrado: " + path);
			this.data = await res.json();
		} catch (e) {
			console.error("No se pudo cargar el archivo de traducción:", e);
			this.data = {};
		}
	},

	translatePage() {
		document.querySelectorAll("[data-i18n]").forEach(el => {
			const key = el.getAttribute("data-i18n");
			if (this.data[key]) el.innerHTML = this.data[key];
		});

		document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
			const key = el.getAttribute("data-i18n-placeholder");
			if (this.data[key]) el.placeholder = this.data[key];
		});

		document.querySelectorAll("[data-i18n-value]").forEach(el => {
			const key = el.getAttribute("data-i18n-value");
			if (this.data[key]) el.value = this.data[key];
		});
	}
};
