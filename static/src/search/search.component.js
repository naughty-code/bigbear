function searchController($http, $mdDialog) {
	var ctrl = this;
	ctrl.loading = false;
	ctrl.showTable = false;
	ctrl.buttonDisabled = false;
	ctrl.lastDivPosition = "center center";

	ctrl.changeEndDate = function () {
		if (ctrl.startDate)
			if (ctrl.startDate > ctrl.endDate)
				ctrl.startDate = ctrl.endDate
	}
	

	ctrl.vrms = ["BBCC", "DBB", "VACASA", "BBV"];
	ctrl.vrmSelected = [];
	ctrl.tiers = ["BRONZE", "SILVER", "GOLD", "PLATINUM"];
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

		ctrl.showTable = false;
		ctrl.loading = true;
		ctrl.buttonDisabled = true;
		ctrl.lastDivPosition = "center center";

		var requestBody = {
			startDate: moment.utc(ctrl.startDate).format('YYYY-MM-DD'),
			endDate: moment.utc(ctrl.endDate).format('YYYY-MM-DD'),
			vrms: ctrl.vrmSelected,
			tiers: ctrl.tierSelected
		}
		$http.post(`http://${host}:5001/api/search/daterange`, requestBody)
			.then(function (result) {
				ctrl.result = [];
				for (const area of result.data.result) {
					var area_temp = {
						title: area.title,
						values: []
					}
					for (const tier of ctrl.tierSelected) {
						var tier_temp = {
							tier: tier,
							values: []
						}
						for (let index = 1; index < 9; index++) {
							let find = area.values.find( v => {
								return (v.tier == tier && v.bedrooms == index)
							})
							if (find)
								tier_temp.values.push(find.avg)
							else
								tier_temp.values.push('0')
						}
						area_temp.values.push(tier_temp)
					}
					ctrl.result.push(area_temp);
				}
				ctrl.loading = false;
				ctrl.showTable = true;
				ctrl.buttonDisabled = false;
				ctrl.lastDivPosition = "center start";
			}, function (result) {
				console.log(result)
			});


		ctrl.addons = [
			{
				name: "Spa",
				value: "--"
			},
			{
				name: "WIFI",
				value: "--"
			},
			{
				name: "Game room or table",
				value: "--"
			}
		]
		ctrl.tierTotals = [
			{
				name: "Platinum",
				value: "--"
			},
			{
				name: "Gold",
				value: "--"
			},
			{
				name: "Silver",
				value: "--"
			},
			{
				name: "Bronze",
				value: "--"
			}
		]
		ctrl.areaTotals = [
			{
				name: "Prime",
				value: "--"
			},
			{
				name: "Medium Demand",
				value: "--"
			},
			{
				name: "Low Demand",
				value: "--"
			}
		]
		ctrl.statisticals = [
			{
				name: "Percent booked/Vacant shown",
				value: "-- / --"
			},
			{
				name: "Market Share",
				value: "--"
			},
			{
				name: "Occupancy over or under ours",
				value: "--"
			},
			{
				name: "bookings in last week",
				value: "--"
			},
			{
				name: "Bookings in last month",
				value: "--"
			},
			{
				name: "Bookings last year",
				value: "--"
			}
		]
		
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