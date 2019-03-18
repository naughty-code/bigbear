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
	ctrl.statistics = [];
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
				for (var area of result.data.result) {
					var area_temp = {
						title: area.title,
						values: []
					}
					for (var tier of ctrl.tierSelected) {
						var tier_temp = {
							tier: tier,
							values: []
						}
						for (var index = 1; index < 9; index++) {
							var find = area.values.find( v => {
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
					ctrl.statistics = result.data.statistics;
				}
				for (var sta of ctrl.statistics) {
					var total = sta['total_category'];
					sta['total_category'] = [];
					for (var tier of ctrl.tierSelected) {
						var tier_temp = {
							name: tier,
							value: 0
						}
						var find = total.find( t => {
							return (t.tier == tier)
						})
						if (find)
							tier_temp.value = find.count;
						sta['total_category'].push(tier_temp);
				}
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