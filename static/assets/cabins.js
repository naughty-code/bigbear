$(document).ready(function() {
	var alertErrorCabins = $('#alert-danger-cabins')
	var progressBarCabins = $('#progress-cabins')
	progressBarCabins.removeClass('d-none')
	alertErrorCabins.addClass('d-none')

	function loadCabins() {
		$.get('/api/cabins')
			.then(function( data ) {
				progressBarCabins.addClass('d-none')
				$('#cabins').DataTable( {
					data: data,
					columns: [
						{ title: "IDVRM" },
						{ title: "ID" },
						{ title: "NAME" },
						{ title: "WEBSITE" },
						{
							title: "DESCRIPTION",
							render: function ( data, type, row ) {
								return `<span class="d-inline-block text-truncate" style="max-width: 150px;" title="${data}">
								${data}</span>`;
							}
						},
						{ title: "ADRESS" },
						{ title: "LOCATION" },
						{ title: "BEDROOMS" },
						{ title: "OCCUPANCY" },
						{ title: "TIER" },
						{ title: "STATUS" }
					]
				});
			})
			.fail(function() {
				progressBarCabins.addClass('d-none')
				alertErrorCabins.removeClass('d-none')
			})
	}
	loadCabins();
});