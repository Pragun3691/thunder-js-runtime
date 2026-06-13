let numbers = [1, 2, 3, 4];

let result = numbers
    .filter(x => x % 2 === 0)
    .map(x => x * 10);

console.log(result.join(", "));
console.log(numbers.reduce((sum, x) => sum + x, 0));
console.log(numbers.find(x => x > 2));
console.log(numbers.some(x => x === 4));
console.log(numbers.every(x => x > 0));
