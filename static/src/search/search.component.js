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
	ctrl.tiers = ["Bronze", "Silver", "Gold", "Platinum"];
	ctrl.tierSelected = [];
	ctrl.result = [];
	ctrl.addons = [];
	ctrl.statisticals = [];
	ctrl.tierTotals = [];
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

	ctrl.search = function(ev) {
		// if (!validFilters()) {
		// 	$mdDialog.show(
		// 		$mdDialog.alert()
		// 		.parent(angular.element(document.querySelector('#popupContainer')))
		// 		.clickOutsideToClose(true)
		// 		.title('Missing filters!')
		// 		.textContent('You need to set all the filters to achieve the search.')
		// 		.ariaLabel('Alert Dialog')
		// 		.ok('Got it!')
		// 		.targetEvent(ev)
		// 	);
		// 	return;
		// }

		var requestBody = {
			startDate: moment.utc(ctrl.startDate).format('YYYY-MM-DD'),
			endDate: moment.utc(ctrl.endDate).format('YYYY-MM-DD'),
			vrms: ctrl.vrmSelected,
			tiers: ctrl.tierSelected
		}
		console.log(requestBody)
		// $http.post(`http://${host}:5001/api/search/avg`, data)

		ctrl.result = [
			{
				title: "Prime Area",
				values: [
					{
						tier: "Platinum",
						values: ['$565', '$645', '$282', '$3543', '$544', '$544', '$321', '$224']
					},
					{
						tier: "Gold",
						values: ['$565', '$645', '$282', '$3543', '$544', '$544', '$321', '$224']
					},
				]
			}
		];
		ctrl.addons = [
			{
				name: "Spa",
				value: "$50.00"
			},
			{
				name: "WIFI",
				value: "$20.00"
			},
			{
				name: "Game room or table",
				value: "$50.00"
			}
		]
		ctrl.tierTotals = [
			{
				name: "Platinum",
				value: "100"
			},
			{
				name: "Gold",
				value: "250"
			},
			{
				name: "Silver",
				value: "205"
			},
			{
				name: "Bronze",
				value: "300"
			}
		]
		ctrl.areaTotals = [
			{
				name: "Prime",
				value: "100"
			},
			{
				name: "Medium Demand",
				value: "250"
			},
			{
				name: "Low Demand",
				value: "205"
			}
		]
		ctrl.statisticals = [
			{
				name: "Percent booked/Vacant shown",
				value: "50% / 50%"
			},
			{
				name: "Market Share",
				value: "50%"
			},
			{
				name: "occupancy over or under ours",
				value: "50%"
			},
			{
				name: "bookings in last week",
				value: "50"
			},
			{
				name: "bookings in last month",
				value: "50"
			},
			{
				name: "Bookings last year",
				value: "200"
			}
		]
		
		ctrl.showTable = false;
		ctrl.loading = true;
		ctrl.buttonDisabled = true;
		ctrl.lastDivPosition = "center center";

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
			ctrl.loading = false;
			ctrl.showTable = true;
			ctrl.buttonDisabled = false;
			ctrl.lastDivPosition = "center start";
	// 	// })

	}

	ctrl.backToSearch = function(ev) {
		ctrl.showTable = false;
		ctrl.loading = false;
		ctrl.buttonDisabled = false;
		ctrl.lastDivPosition = "center center";
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
}
angular.
	module("search").
	component("search", {
		templateUrl: "src/search/search.template.html",
		controller: searchController
	});