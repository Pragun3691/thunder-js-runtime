let functions = [];

for (let i = 0; i < 5; i++) {
    if (i === 2) {
        continue;
    }

    functions.push(() => i);
    functions.push(() => i * 10);
}

for (const fn of functions) {
    console.log(fn());
}