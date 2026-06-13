function apply(value, callback) {
    return callback(value);
}

function makeCounter() {
    let count = 0;

    return function() {
        count += 1;
        return count;
    };
}

const double = x => x * 2;
const counter = makeCounter();

console.log(apply(5, double));
console.log(counter());
console.log(counter());
