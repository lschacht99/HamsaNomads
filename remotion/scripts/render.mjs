import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition} from '@remotion/renderer';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(__dirname, '..');

const valueAfter = (flag) => {
  const index = process.argv.indexOf(flag);
  return index === -1 ? undefined : process.argv[index + 1];
};

const recipePath = valueAfter('--recipe');
const videoPath = valueAfter('--video');
const outputPath = valueAfter('--out');

if (!recipePath || !videoPath || !outputPath) {
  console.error('Usage: npm run render -- --recipe edit_recipe.json --video input.mp4 --out output.mp4');
  process.exit(1);
}

const recipe = JSON.parse(await readFile(path.resolve(recipePath), 'utf8'));
const serveUrl = await bundle({
  entryPoint: path.join(projectRoot, 'src', 'index.tsx'),
  webpackOverride: (config) => config,
});
const inputProps = {
  recipe,
  videoSrc: pathToFileURL(path.resolve(videoPath)).href,
};
const composition = await selectComposition({
  serveUrl,
  id: 'HamsaNomadsVideo',
  inputProps,
});

await renderMedia({
  composition,
  serveUrl,
  codec: 'h264',
  outputLocation: path.resolve(outputPath),
  inputProps,
  chromiumOptions: {
    gl: 'angle',
  },
});
