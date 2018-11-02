$(document).ready(function() {
	var alertErrorFeature = $('#alert-danger-feature')
	var progressBarFeature = $('#progress-feature')
	progressBarFeature.removeClass('d-none')
	alertErrorFeature.addClass('d-none')

	function loadFeature() {
		$.get('/api/features')
			.then(function (data) {
				progressBarFeature.addClass('d-none')
				$('#features').DataTable({
					data: data,
					columns: [
						{ title: "ID" },
						{ title: "FEATURE" }
					]
				});
			})
			.fail(function() {
				progressBarFeature.addClass('d-none')
				alertErrorFeature.removeClass('d-none')
			})
	}
	loadFeature();
});