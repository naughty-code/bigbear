$(document).ready(function() {
	function search() {
		var alertErrorCabins = $('#alert-danger-cabins')
		var progressBarCabins = $('#progress-cabins')

		var alertErrorVRM = $('#alert-danger-vrm')
		var progressBarVRM = $('#progress-vrm')

		progressBarCabins.removeClass('d-none')
		alertErrorCabins.addClass('d-none')
		progressBarVRM.removeClass('d-none')
		alertErrorVRM.addClass('d-none')

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
								${data}
							  </span>`;
							}
						},
						{ title: "ADRESS" },
						{ title: "LOCATION" },
						{ title: "BEDROOMS" },
						{ title: "OCCUPANCY" },
						{ title: "TIER" },
						{ title: "STATUS" }
					]
				} );
				return $.get('/api/vrm');
			})
			.done(function (data) {
				progressBarVRM.addClass('d-none')
				$('#vrm').DataTable( {
					data: data,
					columns: [
						{ title: "IDVRM" },
						{ title: "NAME" },
						{ title: "WEBSITE" },
						{ title: "CABINS" },
						{ title: "LAST SCRAPE" }
					]
				} );
			})
			.fail(function() {
				progressBarCabins.addClass('d-none')
				alertErrorCabins.removeClass('d-none')
				progressBarVRM.addClass('d-none')
				alertErrorVRM.removeClass('d-none')
			})
	}
	search();
});