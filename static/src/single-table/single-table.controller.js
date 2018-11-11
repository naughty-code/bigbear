function singleTableController($scope, $http, $routeParams) {
	var ctrl = $scope;
	$scope.loading = true;
	var masterView = {
		"vrm": "VRM",
		"cabins" : "Cabins",
		"features": "Features",
		"availability": "Availability",
		"report": "Report",
		"advance-report": "Advance Report"
	}
	var view = 'vrm';
	if ($routeParams.view)
		view = $routeParams.view;

	ctrl.header = masterView[view];
	ctrl.gridOptions = {
		enableSorting: true,
		enableFiltering: true,
		minimumColumnSize: 150
	};
	$http.get('/api/' + view)
		.then(function(response) {
			for (const key in response.data[0]) {
				if (response.data[0].hasOwnProperty(key)) {
					ctrl.gridOptions.columnDefs.push({
						field: key,
						cellTooltip: true
					})
				}
			}
			$scope.loading = false;
			ctrl.gridOptions.data = response.data;
		}, function(response) {
			var data = response.data || 'Request failed';
			var status = response.status;
			console.log(status, data);
		});
}

angular.
	module("single-table").
	controller("singleTableController", singleTableController);