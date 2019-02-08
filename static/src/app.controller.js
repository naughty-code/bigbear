angular.module('app').controller('appController', function ($scope, $mdSidenav, $http, $interval, $route) {
	$scope.toggleMenu = function() {
		$mdSidenav('left').toggle();
	}

	$scope.disableButton = true;
	$scope.textUpdate = 'Updating'
	$scope.lastUpdate = '';
	
	$scope.update = function() {
		$scope.disableButton = true;
		$http.post('http://74.91.126.179:5001/api/update', {vrm: $scope.vrmSelected});
		// $http.post('http://localhost:5001/api/update', {vrm: $scope.vrmSelected});
	}

	$scope.vrms = [
		'DBB',
		'VACASA',
		'BBCC',
		'BBV',
		'ALL'
	]
	$scope.vrmSelected = ['ALL']

	var before = ["Updating", ""];
	$interval(function () {
		// $http.get('http://74.91.126.179:5001/api/check')
		$http.get('http://localhost:5001/api/check')
			.then(function(response) {
				if (response.data[0].status == "Updated") {
					$scope.disableButton = false;
					$scope.textUpdate = 'Update now'
					if (before[0] == 'Updating' && before[1] == 'Updating')
						$route.reload();
					before[1] = before[0];
					before[0] = 'Updated';
				}
				else {
					$scope.disableButton = true;
					$scope.textUpdate = 'Updating'
					before[1] = before[0];
					before[0] = 'Updating';
				}
				$scope.lastUpdate = response.data[0]['last_update'];
			}, function(response) {
				var data = response.data || 'Request failed';
				var status = response.status;
				console.log(status, data);
			});
	}, 10000);
})