$(document).ready(function() {
	var alertErrorVRM = $('#alert-danger-vrm')
	var progressBarVRM = $('#progress-vrm')
	progressBarVRM.removeClass('d-none')
	alertErrorVRM.addClass('d-none')

	function loadVRM() {
		$.get('/api/vrm')
			.then(function (data) {
				progressBarVRM.addClass('d-none')
				$('#vrm').DataTable({
					data: data,
					columns: [
						{ title: "IDVRM" },
						{ title: "NAME" },
						{ title: "WEBSITE" },
						{ title: "CABINS" },
						{ title: "LAST SCRAPE" }
					]
				});
			})
			.fail(function() {
				progressBarVRM.addClass('d-none')
				alertErrorVRM.removeClass('d-none')
			})
	}
	loadVRM();
});