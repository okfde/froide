const path = require('path')
const LiveReloadPlugin = require('webpack-livereload-plugin')
const UglifyJsPlugin = require('uglifyjs-webpack-plugin')
const OptimizeCssAssetsPlugin = require('optimize-css-assets-webpack-plugin')
const CopyWebpackPlugin = require('copy-webpack-plugin')
const MiniCssExtractPlugin = require('mini-css-extract-plugin')
const VueLoaderPlugin = require('vue-loader/lib/plugin')

const webpack = require('webpack')

const devMode = process.env.NODE_ENV !== 'production'

const config = {
  entry: {
    main: ['./frontend/javascript/main.js'],
    publicbody: ['./frontend/javascript/publicbody.js'],
    makerequest: ['./frontend/javascript/makerequest.js'],
    request: ['./frontend/javascript/request.js'],
    redact: ['./frontend/javascript/redact.js'],
    tagautocomplete: ['./frontend/javascript/tagautocomplete.js']
  },
  output: {
    path: path.resolve(__dirname, 'froide/static/js'),
    filename: '[name].js',
    library: ['Froide', 'components', '[name]'],
    libraryTarget: 'umd'
  },
  devtool: 'source-map', // any "source-map"-like devtool is possible
  resolve: {
    modules: ['node_modules', 'froide/static'],
    extensions: ['.js', '.vue', '.json'],
    alias: {
      'vue$': 'vue/dist/vue.esm.js',
      'froide': path.resolve('.'),
      'froide_static': path.resolve('.', 'froide', 'static')
    }
  },
  module: {
    rules: [
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
        test: /\.scss$/,
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
              ident: 'postcss',
              plugins: (loader) => [
                require('autoprefixer')()
              ]
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
              includePaths: [
                'node_modules/'
              ]
            }
          }
        ]
      },
      {
        test: /(\.(woff2?|eot|ttf|otf)|font\.svg)(\?.*)?$/,
        loader: 'url-loader',
        options: {
          limit: 10000,
          name: '../fonts/[name].[ext]',
          emitFile: true,
          context: 'froide/static/',
          publicPath: ''
        }
      },
      {
        test: /\.(jpg|png|svg)$/,
        use: {
          loader: 'url-loader',
          options: {
            limit: 8192,
            name: '[path][name].[ext]',
            emitFile: false,
            context: 'froide/static',
            publicPath: '../'
          }
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
    new CopyWebpackPlugin([
      {from: 'node_modules/pdfjs-dist/build/pdf.worker.min.js'}
    ]),
    new webpack.ProvidePlugin({
      $: 'jquery',
      jQuery: 'jquery',
      Popper: ['popper.js/dist/popper.js', 'default']
    }),
    new webpack.DefinePlugin({
      'process.env': {
        NODE_ENV: `"${process.env.NODE_ENV}"`
      }
    })
  ],
  optimization: {
    minimizer: [
      new UglifyJsPlugin({
        cache: true,
        parallel: true,
        sourceMap: true // set to true if you want JS source maps
      })
    ].concat(!devMode ? [
      new OptimizeCssAssetsPlugin({
        assetNameRegExp: /\.css$/,
        cssProcessorOptions: {
          discardComments: { removeAll: true }
        }
      })
    ] : [])
  }
}

module.exports = config
