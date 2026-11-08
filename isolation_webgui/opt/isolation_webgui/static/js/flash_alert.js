window.addEventListener('DOMContentLoaded', () => {
	const toasts = document.querySelectorAll('.toast');
	toasts.forEach((toast) => {
		setTimeout(() => {
			toast.classList.add('hide');
		}, 3000);
		toast.addEventListener('click', () => {
			toast.classList.add('hide');
		});
	});
});
