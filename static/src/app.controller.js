angular.module('app').controller('appController', function ($scope, $mdSidenav, $http, $interval) {
	$scope.toggleMenu = function() {
		$mdSidenav('left').toggle();
	}

	$scope.disableButton = true;
	
	$scope.update = function() {
		$scope.disableButton = true;
		$http.get('http://localhost:5000/api/update');
	}

	$interval(function () {
		$http.get('http://localhost:5000/api/check')
			.then(function(response) {
				console.log(response.data[0].status);
				if (response.data[0].status == "Updated")
					$scope.disableButton = false;
				else
					$scope.disableButton = true;
			}, function(response) {
				var data = response.data || 'Request failed';
				var status = response.status;
				console.log(status, data);
			});
	}, 10000);
})