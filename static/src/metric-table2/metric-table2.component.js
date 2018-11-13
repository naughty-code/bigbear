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
		"Most Popular Bookings",
		"Less Popular VRM",
		"Less Popular Booking",
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
	ctrl.consult = function () {
		$http.get('http://localhost:5000/api/metrics2', {
			params: { 
				year: ctrl.selectedYear,
				day: ctrl.selectedDay
			}
		})
			.then(function (response) {
				var data = response.data[0];
				console.log(data);
				
				ctrl.rows1[0] = (data.bookings)
				// ctrl.rows1[1] = (data[1].vacants)
				
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