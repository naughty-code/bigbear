function singleTableController($scope, $http, $routeParams) {
	var ctrl = $scope;
	$scope.loading = true;
	var view = 'vrm';
	if ($routeParams.view)
		view = $routeParams.view;

	ctrl.gridOptions = {
		enableSorting: true,
		enableFiltering: true,
		minimumColumnSize: 150
	};
	$http.get('http://74.91.126.179:5001/api/' + view)
	// $http.get('http://localhost:5001/api/' + view)
		.then(function(response) {
			for (const key in response.data[0]) {
				if (response.data[0].hasOwnProperty(key)) {
					ctrl.gridOptions.columnDefs.push({
						field: key,
						cellTooltip: true,
						displayName: key
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