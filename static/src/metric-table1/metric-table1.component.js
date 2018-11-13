function metricTable1Controller($http, $filter) {
	var ctrl = this;
	ctrl.header = [
		"Most Booked Holiday",
		"Less Booked Holiday",
		"Cheapest Holiday",
		"Most Expesive Holiday",
		"Most Booked Date",
		"Less Booked Date",
		"Cheapest Date",
		"Most Expesive Date"
	]
	ctrl.rows = []
	$http.get('http://74.91.126.179:5000/api/metrics1')
	// $http.get('http://localhost:5000/api/metrics1')
		.then(function(response) {
			var result = response.data;
			
			ctrl.rows[0] = result[0][0].name + " - " + result[0][0].count;
			ctrl.rows[1] = result[0][result[0].length-1].name + " - " + result[0][result[0].length-1].count;
			ctrl.rows[2] = result[1][0].name;
			ctrl.rows[3] = result[2][0].name;
			ctrl.rows[4] = result[3][0].name + ': ' + $filter('date')(new Date(result[3][0].check_in), 'mediumDate', 'GMT') + ' - ' + $filter('date')(new Date(result[3][0].check_out), 'mediumDate', 'GMT');
			ctrl.rows[5] = result[3][result[3].length-1].name + ': ' + $filter('date')(new Date(result[3][result[3].length-1].check_in), 'mediumDate', 'GMT') + ' - ' + $filter('date')(new Date(result[3][result[3].length-1].check_out), 'mediumDate', 'GMT');
			ctrl.rows[6] = result[4][0].name + ': ' + $filter('date')(new Date(result[4][0].check_in), 'mediumDate', 'GMT') + ' - ' + $filter('date')(new Date(result[4][0].check_out), 'mediumDate', 'GMT');
			ctrl.rows[7] = result[5][result[5].length-1].name + ': ' + $filter('date')(new Date(result[5][result[5].length-1].check_in), 'mediumDate', 'GMT') + ' - ' + $filter('date')(new Date(result[5][result[5].length-1].check_out), 'mediumDate', 'GMT');
		}, function(response) {
			var data = response.data || 'Request failed';
			var status = response.status;
			console.log(status, data);
		});
}
angular.
	module("metric-table1").
	component("metricTable1", {
		templateUrl: "src/metric-table1/metric-table1.template.html",
		controller: metricTable1Controller
	});