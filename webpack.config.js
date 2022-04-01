const path = require('path')
const LiveReloadPlugin = require('webpack-livereload-plugin')
const TerserPlugin = require('terser-webpack-plugin')
const CssMinimizerPlugin = require('css-minimizer-webpack-plugin')
const CopyWebpackPlugin = require('copy-webpack-plugin')
const MiniCssExtractPlugin = require('mini-css-extract-plugin')
const VueLoaderPlugin = require('vue-loader/lib/plugin')

const webpack = require('webpack')

const devMode = process.env.NODE_ENV !== 'production'

const ENTRY = {
  main: ['./frontend/javascript/main.ts'],
  document: ['./frontend/javascript/document.js'],
  docupload: ['./frontend/javascript/docupload.js'],
  filingcabinet: '@okfde/filingcabinet/frontend/javascript/filingcabinet.js',
  geomatch: ['./frontend/javascript/geomatch.js'],
  makerequest: ['./frontend/javascript/makerequest.js'],
  messageredaction: ['./frontend/javascript/messageredaction.js'],
  moderation: ['./frontend/javascript/moderation.js'],
  publicbody: ['./frontend/javascript/publicbody.js'],
  publicbodyupload: ['./frontend/javascript/publicbodyupload.js'],
  redact: ['./frontend/javascript/redact.js'],
  request: ['./frontend/javascript/request.ts'],
  'request-alpha': ['./frontend/javascript/alpha/request-alpha.ts'],
  tagautocomplete: ['./frontend/javascript/tagautocomplete.ts'],
  fileuploader: ['./frontend/javascript/fileuploader.js']
}

const EXCLUDE_CHUNKS = ['main', 'tagautocomplete'].join('|')

let CHUNK_LIST = []
for (const key in ENTRY) {
  if (EXCLUDE_CHUNKS.indexOf(key) !== -1) {
    continue
  }
  CHUNK_LIST.push(key)
}
CHUNK_LIST = CHUNK_LIST.join('|')

const config = {
  entry: ENTRY,
  output: {
    path: path.resolve(__dirname, 'froide/static/js'),
    filename: '[name].js',
    library: ['Froide', 'components', '[name]'],
    libraryTarget: 'umd'
  },
  devtool: 'source-map', // any "source-map"-like devtool is possible
  resolve: {
    modules: ['node_modules', 'froide/static'],
    extensions: ['.js', '.ts', '.vue', '.json'],
    alias: {
      vue$: 'vue/dist/vue.esm.js',
      froide: path.resolve('.')
    },
    fallback: { zlib: false }
  },
  module: {
    rules: [
      {
        test: /bootstrap\.native$/,
        use: {
          loader: 'bootstrap.native-loader',
          options: {
            only: ['modal', 'dropdown', 'collapse', 'alert', 'tab', 'tooltip']
          }
        }
      },
      {
        test: /\.ts$/,
        exclude: /node_modules/,
        use: [
          // {
          //   loader: 'babel-loader',
          //   options: {
          //     presets: [path.resolve('./node_modules/babel-preset-env')],
          //     babelrc: false,
          //     plugins: [
          //       require('babel-plugin-transform-object-rest-spread')
          //     ]
          //   }
          // },
          {
            loader: 'ts-loader'
          }
        ]
      },
      {
        test: /\.js$/,
        include: /(froide\/frontend|node_modules\/(bootstrap))/,
        use: {
          loader: 'babel-loader'
        }
      },
      {
        test: /\.vue/,
        use: {
          loader: 'vue-loader'
        }
      },
      {
        test: /\.s?css$/,
        use: [
          devMode ? 'vue-style-loader' : MiniCssExtractPlugin.loader,
          {
            loader: 'css-loader',
            options: {
              sourceMap: true
            }
          },
          {
            loader: 'postcss-loader',
            options: {
              postcssOptions: {
                plugins: [['autoprefixer']]
              }
            }
          },
          {
            loader: 'resolve-url-loader',
            options: {
              sourceMap: true
            }
          },
          {
            loader: 'sass-loader',
            options: {
              sourceMap: true,
              sassOptions: {
                includePaths: ['node_modules/']
              }
            }
          }
        ]
      },
      {
        test: /(\.(woff2?|eot|ttf|otf)|font\.svg)(\?.*)?$/,
        type: 'asset/resource',
        generator: {
          filename: '../fonts/[name][ext]'
        }
      },
      {
        test: /\.(jpg|png|svg)$/,
        type: 'asset',
        parser: {
          dataUrlCondition: {
            maxSize: 4 * 1024
          }
        },
        generator: {
          filename: '../img/[name][ext]'
        }
      }
    ]
  },
  plugins: [
    new VueLoaderPlugin(),
    new MiniCssExtractPlugin({
      // Options similar to the same options in webpackOptions.output
      // both options are optional
      filename: '../css/[name].css'
      // publicPath: '../../'
    }),
    new LiveReloadPlugin(),
    new CopyWebpackPlugin({
      patterns: [{ from: 'node_modules/pdfjs-dist/build/pdf.worker.min.js' }]
    }),
    new webpack.DefinePlugin({
      'process.env': {
        NODE_ENV: `"${process.env.NODE_ENV}"`
      },
      global: 'window'
    })
  ],
  optimization: {
    minimizer: [new TerserPlugin()].concat(
      !devMode ? [new CssMinimizerPlugin()] : []
    ),
    splitChunks: {
      cacheGroups: {
        pdfjs: {
          test: /[\\/]node_modules[\\/](pdfjs-dist\/build\/pdf\.js)/,
          name: 'pdfjs',
          chunks: 'all'
        },
        common: {
          test: /[\\/]node_modules[\\/]/,
          chunks(chunk) {
            return CHUNK_LIST.indexOf(chunk.name) !== -1
          },
          name: 'common',
          minChunks: 2,
          minSize: 0
        }
      }
    }
  }
}

module.exports = config
