angular.module('app').controller('appController', function ($scope, $mdSidenav) {
	console.log('test');
	$scope.toggleMenu = function() {
		$mdSidenav('left').toggle();
	}
})