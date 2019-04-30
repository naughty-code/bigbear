function metricTable2Controller($http) {
	var ctrl = this;
	ctrl.years = [
		"2018",
		"2019"
	]
	ctrl.selectedYear = ctrl.years[0];
	ctrl.holidays = [
		"MLK Day",
		"Easter",
		"President's Day",
		"Labor Day",
		"Memorial Day",
		"Christmas Season",
		"Veteran’s Day",
		"St Patrick’s Day",
		"Thanksgiving",
		"Cinco de Mayo",
		"4th of July",
		"Columbus Day"
	]
	ctrl.selectedDay = ctrl.holidays[0];
	ctrl.header1 = [
		"Bookings",
		"Vacants",
		"Most Popular VRM",
		"Most Popular VRM Bookings",
		"Less Popular VRM",
		"Less Popular VRM Booking",
		"Our Bookings",
		"Our Vacants"
	]
	ctrl.header2 = [
		"AVG Bookings Rate",
		"AVG Cheapest VRM",
		"AVG Most Expensive VRM",
		"Most Popular Tier",
		"Cheapest Cabin Booked",
		"Most Expensive Cabin Booked",
		"Cheapest Cabin",
		"Most Expensive Cabin"
	]
	ctrl.header3 = [
		"Most Popular Location",
		"Less Popular Location",
		"Most Popular Ocuppancy",
		"Less Popular Ocupancy"
	]
	ctrl.rows1 = []
	ctrl.rows2 = []
	ctrl.rows3 = []
	ctrl.consult = function () {
		$http.get('http://35.203.21.194:5001/api/metrics2', {
		// $http.get('http://localhost:5001/api/metrics2', {
			params: { 
				year: ctrl.selectedYear,
				day: ctrl.selectedDay
			}
		})
			.then(function (response) {
				var data = response.data;
				console.log(data);
				
				ctrl.rows1[0] = data[0][0].bookings
				ctrl.rows1[1] = data[1][0].vacants
				ctrl.rows1[2] = data[2][0].idvrm
				ctrl.rows1[3] = data[2][0].count
				ctrl.rows1[4] = data[2][1].idvrm
				ctrl.rows1[5] = data[2][1].count

				ctrl.rows2[0] = data[3][0].avg
				ctrl.rows2[1] = data[4][0].idvrm + ' - ' + data[4][0].avg
				ctrl.rows2[2] = data[4][data[4].length-1].idvrm + ' - ' + data[4][data[4].length-1].avg
				ctrl.rows2[4] = 0;
				ctrl.rows2[5] = 0;
				if (data[5].length > 0) {
					ctrl.rows2[6] = data[5][data[5].length-1].id + ' - ' + data[5][data[5].length-1].rate
					ctrl.rows2[7] = data[5][0].id + ' - ' + data[5][0].rate
				}
				else {
					ctrl.rows2[6] = 0
					ctrl.rows2[7] = 0
				}

				ctrl.rows3[0] = data[6][0].location;
				ctrl.rows3[1] = data[6][data[6].length-1].location
				ctrl.rows3[2] = data[7][0].occupancy;
				ctrl.rows3[3] = data[7][data[7].length-1].occupancy

			}, function (response) {
				var data = response.data || 'Request failed';
				var status = response.status;
				console.log(status, data);
			})
	}
	ctrl.consult();
}
angular.
	module("metric-table2").
	component("metricTable2", {
		templateUrl: "src/metric-table2/metric-table2.template.html",
		controller: metricTable2Controller
	});