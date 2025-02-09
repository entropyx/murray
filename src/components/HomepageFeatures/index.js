import clsx from 'clsx';
import Heading from '@theme/Heading';
import styles from './styles.module.css';

const FeatureList = [
  {
    title: 'Easy to Use',
    Svg: require('@site/static/img/facil-de-usar.svg').default,
    description: (
      <>
        Murray was built with the purpose of providing an easy-to-use 
        tool for geographic incrementality testing for any user.
      </>
    ),
  },
  {
    title: 'Real results',
    Svg: require('@site/static/img/resultados.svg').default,
    description: (
      <>
        It features robust methods used to generate reliable results.
        </>
    ),
  },
  {
    title: 'Flexibility, a single purpose',
    Svg: require('@site/static/img/flexibilidad.svg').default,
    description: (
      <>
        There are two ways to use Murray: a more user-friendly approach 
        and a more technical one that provides additional tools.
      </>
    ),
  },
];

function Feature({Svg, title, description}) {
  return (
    <div className={clsx('col col--4')}>
      <div className="text--center">
      <Svg className={styles.featureSvg} role="img" style={{ width: "60px", height: "auto" }} />
      </div>
      <div className="text--center padding-horiz--md">
        <Heading as="h3">{title}</Heading>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures() {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
