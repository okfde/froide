const path = require('path')
const ExtractTextPlugin = require('extract-text-webpack-plugin')
const LiveReloadPlugin = require('webpack-livereload-plugin')
const UglifyJsPlugin = require('uglifyjs-webpack-plugin')
const OptimizeCssAssetsPlugin = require('optimize-css-assets-webpack-plugin')
const CopyWebpackPlugin = require('copy-webpack-plugin')
const webpack = require('webpack')

const extractSass = new ExtractTextPlugin({
  filename: '../css/[name].css',
  disable: process.env.NODE_ENV === 'development'
})

const config = {
  entry: {
    main: ['./frontend/javascript/main.js'],
    publicbody: ['./frontend/javascript/publicbody.js'],
    makerequest: ['./frontend/javascript/makerequest.js'],
    request: ['./frontend/javascript/request.js'],
    redact: ['./frontend/javascript/redact.js']
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
      'vue$': 'vue/dist/vue.esm.js'
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
        use: extractSass.extract({
          use: [{
            loader: 'css-loader',
            options: {
              sourceMap: true
            }
          },
          {
            loader: 'sass-loader',
            options: {
              sourceMap: true,
              includePaths: ['node_modules/']
            }
          }],
          // use style-loader in development
          fallback: 'style-loader'
        })
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
        test: /\.(jpg|png)$/,
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
    extractSass,
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
    }),
    new webpack.optimize.CommonsChunkPlugin({
      name: 'common',
      // (the commons chunk name)

      filename: 'common.js',
      // (the filename of the commons chunk)

      chunks: ['publicbody', 'request', 'makerequest'],
      minChunks: 2
      // (Modules must be shared between 3 entries)
    })
  ].concat(process.env.NODE_ENV === 'production' ? [
    new UglifyJsPlugin({
      sourceMap: true,
      uglifyOptions: {
        ie8: true,
        ecma: 5,
        mangle: false
      }
    }),
    new OptimizeCssAssetsPlugin({
      assetNameRegExp: /\.css$/,
      cssProcessorOptions: { discardComments: { removeAll: true } }
    })] : [])
}

module.exports = config
