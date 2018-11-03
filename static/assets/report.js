
$.fn.dataTable.ext.search.push(
    function( settings, data, dataIndex ) {
		var idvrm_filter = $('#idvrm').val();
		var id_filter = $('#id_search').val();
		var name_filter = $('#name_search').val();
		var checkin_filter = $('#checkin').val();
		var checkout_filter = $('#checkout').val();
		var status_filter = $('#status').val();
		var days_filter = $('#days').val();

        var idvrm_table = data[0];
		var id_table = data[1];
		var name_table = data[2];
		var checkin_table = data[4];
		var checkout_table = data[5];
		var status_table = data[6];
		var days_table = data[8];
 
		if ( (id_table != '' && idvrm_table != '' && name_table != '' && checkin_table != '' && checkout_table != '' && status_table != '' && days_table != '') &&
			id_table.search(id_filter) != -1
			&& idvrm_table.search(idvrm_filter) != -1
			&& name_table.search(name_filter) != -1
			&& checkin_table.search(checkin_filter) != -1
			&& checkout_table.search(checkout_filter) != -1
			&& status_table.search(status_filter) != -1
			&& days_table.search(days_filter) != -1
		)
			return true;

        return false;
    }
);
$(document).ready(function() {
	var alertErrorReport = $('#alert-danger-report')
	var progressBarReport = $('#progress-report')
	var search_table = $('#search-table')
	var table1 = $('#table1')
	progressBarReport.removeClass('d-none')
	alertErrorReport.addClass('d-none')

	function loadReport() {
		$.get('/api/report')
			.then(function (data) {
				progressBarReport.addClass('d-none')
				search_table.removeClass('d-none')
				table1.removeClass('d-none')
				var tbody = $('#table1 tbody')
				data.table1.forEach(data_row => {
					var row = $('<tr></tr>');
					$('<td></td>').text(data_row[0]).appendTo(row);
					$('<td style="text-align: right"></td>').text(data_row[1]).appendTo(row);
					$('<td style="text-align: right"></td>').text(data_row[2]).appendTo(row);
					$('<td style="text-align: right"></td>').text(data_row[3]).appendTo(row);
					row.appendTo(tbody);
				});
				var table2 = $('#report').DataTable({
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
				$('#idvrm, #id_search, #name_search, #checkin, #checkout, #status, #days').keyup( function() {
					table2.draw();
				} );
			})
			.fail(function() {
				progressBarReport.addClass('d-none')
				alertErrorReport.removeClass('d-none')
			})
	}
	loadReport();
});