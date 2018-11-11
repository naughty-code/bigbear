angular.module('app').controller('appController', function ($scope, $mdSidenav) {
	$scope.disableButton = false;
	$scope.toggleMenu = function() {
		$mdSidenav('left').toggle();
	}
	$scope.update = function() {
		$scope.disableButton = true;
	}
})