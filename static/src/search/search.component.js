function searchController($http, $mdDialog) {
	var ctrl = this;
	ctrl.loading = false;
	ctrl.showTable = false;
	ctrl.buttonDisabled = false;
	ctrl.lastDivPosition = "center center";
	ctrl.maxDate = new Date()

	ctrl.changeEndDate = function () {
		if (ctrl.startDate)
			if (ctrl.startDate > ctrl.endDate)
				ctrl.startDate = ctrl.endDate
	}
	

	ctrl.vrms = ["BBCC", "DBB", "VACASA", "BBV"];
	ctrl.vrmSelected = [];
	ctrl.tiers = ["Broze", "Silver", "Gold", "Platinum"];
	ctrl.tierSelected = [];
	ctrl.toggle = function (item, list) {
		var idx = list.indexOf(item);
		if (idx > -1) {
		  list.splice(idx, 1);
		}
		else {
		  list.push(item);
		}
	}
	
	ctrl.exists = function (item, list) {
		return list.indexOf(item) > -1;
	};
	ctrl.isChecked = function(items, selected) {
		return ctrl[selected].length === ctrl[items].length;
	}
	ctrl.isIndeterminate = function(items, selected) {
		return (ctrl[selected].length !== 0 &&
			ctrl[selected].length !== ctrl[items].length);
	}
	ctrl.toggleAll = function(items, selected) {
		if (ctrl[selected].length === ctrl[items].length) {
			ctrl[selected] = [];
		} else if (ctrl[selected].length === 0 || ctrl[selected].length > 0) {
			ctrl[selected] = ctrl[items].slice(0);
		}
	}

	// ctrl.some = function(array, value) {
	// 	if (array)
	// 		return array.some(function(a){
	// 			return a === value;
	// 		})
	// 	else
	// 		return false;
	// }
	var host = "74.91.126.179";
	// var host = "localhost";
	// var promises = [
	// 	$http.get(`http://${host}:5001/api/search/amenities`),
	// 	$http.get(`http://${host}:5001/api/search/vrms`),
	// 	$http.get(`http://${host}:5001/api/search/bedrooms`),
	// 	$http.get(`http://${host}:5001/api/search/years`),
	// 	$http.get(`http://${host}:5001/api/search/days`),
	// 	$http.get(`http://${host}:5001/api/search/tiers`),
	// ]
	// Promise.all(promises).then(function(values) {
	// 	ctrl.amenities = values[0].data;
	// 	ctrl.vrms = values[1].data;
	// 	ctrl.bedrooms = values[2].data;
	// 	ctrl.years = values[3].data;
	// 	ctrl.days = values[4].data;
	// 	ctrl.tiers = values[5].data;

	// 	ctrl.vrmSelected = [];
	// 	for (const vrm of ctrl.vrms) {
	// 		ctrl.vrmSelected.push(vrm);
	// 	}
	// 	});
	// ctrl.compares = [
	// 	'Avg Rate',
	// 	'Max Rate',
	// 	'Min Rate'
	// ]
	// ctrl.shows = [
	// 	'Booking',
	// 	'Vacants'
	// ]
	// ctrl.compareSelected = ctrl.compares;
	// ctrl.showSelected = ctrl.shows;
	ctrl.search = function(ev) {
		if (!validFilters()) {
			$mdDialog.show(
				$mdDialog.alert()
				.parent(angular.element(document.querySelector('#popupContainer')))
				.clickOutsideToClose(true)
				.title('Missing filters!')
				.textContent('You need to set all the filters to achieve the search.')
				.ariaLabel('Alert Dialog')
				.ok('Got it!')
				.targetEvent(ev)
			);
			return;
		}

		var requestBody = {
			startDate: moment.utc(ctrl.startDate).format('YYYY-MM-DD'),
			endDate: moment.utc(ctrl.endDate).format('YYYY-MM-DD'),
			vrms: ctrl.vrmSelected,
			tiers: ctrl.tierSelected
		}
		console.log(requestBody)
		// $http.post(`http://${host}:5001/api/search/avg`, data)

	// 	ctrl.showTable = false;
	// 	ctrl.loading = true;
	// 	ctrl.buttonDisabled = true;
	// 	ctrl.lastDivPosition = "center center";

	// 	// var data = {
	// 	// 	amenities: ctrl.amenitySelected,
	// 	// 	vrms: ctrl.vrmSelected,
	// 	// 	bedrooms: ctrl.bedroomSelected,
	// 	// 	years: ctrl.yearSelected,
	// 	// 	days: ctrl.daySelected,
	// 	// 	tiers: ctrl.tierSelected
	// 	// }

	// 	// var comparePomises = [];
	// 	// if (ctrl.compareSelected.length > 0)
	// 	// 	comparePomises.push($http.post(`http://${host}:5001/api/search/avg`, data));
		
	// 	// Promise.all(comparePomises).then(function (values) {
	// 	// 	console.log(values);
	// 	// 	ctrl.firstData = values[0].data;
	// 	// 	angular.forEach(ctrl.firstData, function(value, key) {
	// 	// 		ctrl.firstData[key].check_in = moment.utc(ctrl.firstData[key].check_in).toDate();
	// 	// 		ctrl.firstData[key].check_out = moment.utc(ctrl.firstData[key].check_out).toDate();
	// 	// 		ctrl.firstData[key].average = ctrl.firstData[key].average ? ctrl.firstData[key].average : '$0';
	// 	// 		ctrl.firstData[key].minimum = ctrl.firstData[key].minimum ? ctrl.firstData[key].minimum : '$0';
	// 	// 		ctrl.firstData[key].maximum = ctrl.firstData[key].maximum ? ctrl.firstData[key].maximum : '$0';
	// 	// 		ctrl.firstData[key]['Bookings %'] = ctrl.firstData[key]['Bookings %'] + '%';
	// 	// 		ctrl.firstData[key]['Vacants %'] = ctrl.firstData[key]['Vacants %'] + '%';
	// 	// 	});
	// 	// 	ctrl.loading = false;
	// 	// 	ctrl.showTable = true;
	// 	// 	ctrl.buttonDisabled = false;
	// 	// 	ctrl.lastDivPosition = "center start";
	// 	// })

	}

	function validFilters() {
		if (!ctrl.startDate || !ctrl.endDate)
			return false;
		if (!ctrl.vrmSelected || ctrl.vrmSelected.length === 0)
			return false;
		if (!ctrl.tierSelected || ctrl.tierSelected.length === 0)
			return false;
		return true;
	}

	// function validFilters() {
	// 	if (!ctrl.amenitySelected || ctrl.amenitySelected.length === 0)
	// 		return false;
	// 	if (!ctrl.vrmSelected || ctrl.vrmSelected.length === 0)
	// 		return false;
	// 	if (!ctrl.bedroomSelected)
	// 		return false;
	// 	if (!ctrl.yearSelected || ctrl.yearSelected.length === 0)
	// 		return false;
	// 	if (!ctrl.daySelected || ctrl.daySelected.length === 0)
	// 		return false;
	// 	if (!ctrl.tierSelected || ctrl.tierSelected.length === 0)
	// 		return false;
	// 	return true;
	// }
}
angular.
	module("search").
	component("search", {
		templateUrl: "src/search/search.template.html",
		controller: searchController
	});