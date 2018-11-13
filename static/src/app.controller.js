angular.module('app').controller('appController', function ($scope, $mdSidenav, $http, $interval, $route) {
	$scope.toggleMenu = function() {
		$mdSidenav('left').toggle();
	}

	$scope.disableButton = true;
	
	$scope.update = function() {
		$scope.disableButton = true;
		$http.get('http://74.91.126.179:5000/api/update');
		// $http.get('http://localhost:5000/api/update');
	}

	var before = ["Updating", ""];
	$interval(function () {
		// $http.get('http://74.91.126.179:5000/api/check')
		$http.get('http://localhost:5000/api/check')
			.then(function(response) {
				if (response.data[0].status == "Updated") {
					$scope.disableButton = false;
					if (before[0] == 'Updating' && before[1] == 'Updating')
						$route.reload();
					before[1] = before[0];
					before[0] = 'Updated';
				}
				else {
					$scope.disableButton = true;
					before[1] = before[0];
					before[0] = 'Updating';
				}
			}, function(response) {
				var data = response.data || 'Request failed';
				var status = response.status;
				console.log(status, data);
			});
	}, 10000);
})