function twoTablesController($scope, $http, $routeParams) {
	var ctrl = $scope;
	$scope.loading = true;
	var view = 'report';
	if ($routeParams.view)
		view = $routeParams.view;

	ctrl.gridOptions = {
		enableSorting: true,
		enableFiltering: true,
		minimumColumnSize: 150
	};
	ctrl.gridOptions2 = {
		enableSorting: true,
		enableFiltering: true,
		minimumColumnSize: 150
	};
	$http.get('http://35.203.21.194:5001/api/' + view)
	// $http.get('http://localhost:5001/api/' + view)
		.then(function(response) {
			for (const key in response.data.table1[0]) {
				if (response.data.table1[0].hasOwnProperty(key)) {
					ctrl.gridOptions.columnDefs.push({
						field: key,
						cellTooltip: true
					})
				}
			}
			$scope.loading = false;
			ctrl.gridOptions.data = response.data.table1;
			for (const key in response.data.table2[0]) {
				if (response.data.table2[0].hasOwnProperty(key)) {
					ctrl.gridOptions2.columnDefs.push({
						field: key,
						cellTooltip: true
					})
				}
			}
			ctrl.gridOptions2.data = response.data.table2;
		}, function(response) {
			var data = response.data || 'Request failed';
			var status = response.status;
			console.log(status, data);
		});
}

angular.
	module("two-tables").
	controller("twoTablesController", twoTablesController);