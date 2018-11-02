$(document).ready(function() {
	var alertErrorReport = $('#alert-danger-report')
	var progressBarReport = $('#progress-report')
	progressBarReport.removeClass('d-none')
	alertErrorReport.addClass('d-none')

	function loadReport() {
		$.get('/api/report')
			.then(function (data) {
				progressBarReport.addClass('d-none')
				var tbody = $('#table1 tbody')
				data.table1.forEach(data_row => {
					var row = $('<tr></tr>');
					$('<td></td>').text(data_row[0]).appendTo(row);
					$('<td style="text-align: right"></td>').text(data_row[1]).appendTo(row);
					$('<td style="text-align: right"></td>').text(data_row[2]).appendTo(row);
					$('<td style="text-align: right"></td>').text(data_row[3]).appendTo(row);
					row.appendTo(tbody);
				});
				$('#report').DataTable({
					data: data.table2,
					columns: [
						{ title: "IDVRM" },
						{ title: "ID" },
						{ title: "NAME" },
						{ title: "WEBSITE" },
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
				progressBarReport.addClass('d-none')
				alertErrorReport.removeClass('d-none')
			})
	}
	loadReport();
});