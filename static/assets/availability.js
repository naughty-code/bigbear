$(document).ready(function() {
	var alertErrorAvailability = $('#alert-danger-availability')
	var progressBarAvailability = $('#progress-availability')
	progressBarAvailability.removeClass('d-none')
	alertErrorAvailability.addClass('d-none')

	function loadAvailability() {
		$.get('/api/availability')
			.then(function (data) {
				progressBarAvailability.addClass('d-none')
				$('#availability').DataTable({
					data: data,
					columns: [
						{ title: "ID" },
						{ 
							title: "CHECK IN",
							render: function ( data ) {
								return moment(data).format("MM-DD-YYYY");
							}
						},
						{ 
							title: "CHECK OUT",
							render: function ( data ) {
								return moment(data).format("MM-DD-YYYY");
							}
						},
						{ title: "STATUS" },
						{ title: "RATE" },
						{ title: "NAME" }
					]
				});
			})
			.fail(function() {
				progressBarAvailability.addClass('d-none')
				alertErrorAvailability.removeClass('d-none')
			})
	}
	loadAvailability();
});