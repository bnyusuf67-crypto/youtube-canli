// get_po_token.js
const { generate } = require('youtube-po-token-generator');

async function main() {
    try {
        const tokenData = await generate();
        // Python tarafına okunabilir JSON basıyoruz
        console.log(JSON.stringify(tokenData));
    } catch (error) {
        console.error(JSON.stringify({ error: error.message }));
        process.exit(1);
    }
}

main();
